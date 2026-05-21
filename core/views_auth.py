from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import (
    LoginForm, ForgotPasswordEmailForm,
    SecurityQuestionSetupForm, SecurityQuestionVerifyForm,
    ResetPasswordForm, SECURITY_QUESTIONS
)
from .models import AuditLog, Employee, AdminSecurityQuestion
from .decorators import get_client_ip


def login_view(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_staff and not user.is_superuser:
                    if hasattr(user, 'employee_profile'):
                        emp = user.employee_profile
                        if emp.status != 'active':
                            messages.error(
                                request,
                                f"Your account is currently {emp.get_status_display()}. "
                                f"Please contact HR for assistance."
                            )
                            return render(request, 'login.html', {'form': form})
                    else:
                        messages.error(request, "No employee profile associated with this account.")
                        return render(request, 'login.html', {'form': form})

                login(request, user)

                AuditLog.objects.create(
                    user        = user,
                    action      = 'login',
                    model_name  = 'User',
                    object_id   = user.id,
                    description = f"User '{user.username}' logged in successfully.",
                    ip_address  = get_client_ip(request),
                )

                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                return _role_redirect(user)
            else:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user        = request.user,
            action      = 'logout',
            model_name  = 'User',
            object_id   = request.user.id,
            description = f"User '{request.user.username}' logged out.",
            ip_address  = get_client_ip(request),
        )
        logout(request)

    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


@login_required(login_url='/login/')
def dashboard_redirect(request):
    return _role_redirect(request.user)


def _role_redirect(user):
    if user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('employee_dashboard')


def forgot_password_email(request):
    if request.method == 'POST':
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user  = User.objects.get(email=email)

            if not hasattr(user, 'security_question'):
                messages.error(request, "No security question set for this account. Please contact your administrator.")
                return render(request, 'forgot_password.html', {'form': form})

            request.session['reset_user_id'] = user.id
            return redirect('forgot_password_verify')
    else:
        form = ForgotPasswordEmailForm()

    return render(request, 'forgot_password.html', {'form': form})


def forgot_password_verify(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password_email')

    try:
        user = User.objects.get(pk=user_id)
        sq   = user.security_question
    except (User.DoesNotExist, AdminSecurityQuestion.DoesNotExist):
        return redirect('forgot_password_email')

    question_display = dict(SECURITY_QUESTIONS).get(sq.question, sq.question)

    if request.method == 'POST':
        form = SecurityQuestionVerifyForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer'].strip().lower()
            if answer == sq.answer.strip().lower():
                request.session['reset_verified'] = True
                return redirect('reset_password')
            else:
                messages.error(request, "Incorrect answer. Please try again.")
    else:
        form = SecurityQuestionVerifyForm()

    return render(request, 'security_questions.html', {
        'form':     form,
        'question': question_display,
    })


def reset_password(request):
    if not request.session.get('reset_verified'):
        return redirect('forgot_password_email')

    user_id = request.session.get('reset_user_id')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('forgot_password_email')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            del request.session['reset_user_id']
            del request.session['reset_verified']
            messages.success(request, "Password reset successfully. You can now log in.")
            return redirect('login')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})


def setup_security_question(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = SecurityQuestionSetupForm(request.POST)
        if form.is_valid():
            question = form.cleaned_data['question']
            answer   = form.cleaned_data['answer'].strip().lower()

            AdminSecurityQuestion.objects.update_or_create(
                user     = request.user,
                defaults = {'question': question, 'answer': answer}
            )
            messages.success(request, "Security question saved successfully.")
            return redirect('admin_dashboard')
    else:
        form = SecurityQuestionSetupForm()

    return render(request, 'setup_security_question.html', {'form': form})