"""
KAVAN v6.0 — Authentication Models
============================================================
Core identity models: User, RefreshToken, EmailVerification,
PasswordReset.

The User model extends AbstractBaseUser + PermissionsMixin so
Django's full auth stack remains available while we supply a
UUID PK, email-based login, and enterprise-grade status enum.

Design decisions:
  - UUIDField PK:   prevents ID enumeration attacks
  - Argon2 hashing: configured via AUTHENTICATION_BACKENDS
  - status enum:    replaces raw boolean flags for clarity
  - TenantMixin:    tenant_id present now (null), populated L3
  - AuditMixin:     created_by/updated_by present now, wired L2
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models.mixins import TimestampMixin


# ============================================================
# USER STATUS ENUM
# ============================================================


class UserStatus(models.TextChoices):
    """
    Explicit user lifecycle states.

    Replaces raw is_active / is_verified booleans to provide
    a clear, auditable lifecycle.
    """
    PENDING  = "PENDING",  _("Pending Email Verification")
    VERIFIED = "VERIFIED", _("Email Verified — Awaiting Activation")
    ACTIVE   = "ACTIVE",   _("Active")
    LOCKED   = "LOCKED",   _("Temporarily Locked")
    SUSPENDED = "SUSPENDED", _("Manually Suspended by Admin")
    DISABLED = "DISABLED", _("Permanently Disabled")
    DELETED  = "DELETED",  _("Soft Deleted")


# ============================================================
# USER MANAGER
# ============================================================


class KavanUserManager(BaseUserManager):
    """
    Custom manager for the User model.
    Provides create_user() and create_superuser().
    """

    def create_user(self, email: str, password: str = None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError(_("Email address is required."))
        email = self.normalize_email(email)
        extra_fields.setdefault("status", UserStatus.PENDING)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields.setdefault("email_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class ActiveUserManager(KavanUserManager):
    """Returns only ACTIVE users (excludes locked, disabled, deleted)."""

    def get_queryset(self):
        return super().get_queryset().filter(status=UserStatus.ACTIVE)


# ============================================================
# USER MODEL
# ============================================================


class User(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    """
    KAVAN Enterprise User Model.

    Primary identity entity. Replaces Django's default auth.User.
    All other models reference this via ForeignKey.

    Authentication:
        USERNAME_FIELD = "email"
        Password hashing via argon2 (configured in settings)

    Layer hooks:
        tenant_id   → Layer 3 (Multi-Tenant Engine)
        roles       → Layer 4 (RBAC, resolved at token time)
        permissions → Layer 4 (RBAC, resolved at token time)
    """

    # ---- Identity ----
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("User ID"),
        help_text="Unique identifier (UUID4). Never changes.",
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name=_("Email Address"),
        help_text="Primary identifier used for login.",
    )
    username = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name=_("Username"),
        help_text="Optional display name. Must be unique if set.",
    )

    # ---- Personal Info ----
    first_name = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("First Name"),
    )
    last_name = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Last Name"),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Phone Number"),
        help_text="E.164 format preferred, e.g. +919876543210",
    )

    # ---- Status & Lifecycle ----
    status = models.CharField(
        max_length=16,
        choices=UserStatus.choices,
        default=UserStatus.PENDING,
        db_index=True,
        verbose_name=_("Account Status"),
        help_text="User lifecycle state. See UserStatus enum.",
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_("Email Verified"),
        help_text="True when the user has clicked the verification link.",
    )

    # ---- Django Required Flags ----
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text="False = account cannot log in. Prefer using `status` instead.",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("Is Staff"),
        help_text="Grants Django admin access.",
    )
    class PlatformRole(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", _("Super Admin")
        PLATFORM_SUPPORT = "PLATFORM_SUPPORT", _("Platform Support")
        PLATFORM_OPERATOR = "PLATFORM_OPERATOR", _("Platform Operator")
        DEVOPS = "DEVOPS", _("DevOps")
        SECURITY_ENGINEER = "SECURITY_ENGINEER", _("Security Engineer")

    platform_role = models.CharField(
        max_length=32,
        choices=PlatformRole.choices,
        null=True,
        blank=True,
        verbose_name=_("Platform Role"),
        help_text="Internal KAVAN platform role. Null = standard tenant user.",
    )

    # ---- MFA ----
    mfa_enabled = models.BooleanField(
        default=False,
        verbose_name=_("MFA Enabled"),
        help_text="True when TOTP MFA is active for this account.",
    )

    # ---- Login Tracking ----
    failed_login_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Failed Login Attempts"),
        help_text="Resets to 0 after successful login.",
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Locked Until"),
        help_text="Account is locked until this datetime. Null = not locked.",
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Login At"),
        help_text="Timestamp of the most recent successful login.",
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Last Login IP"),
        help_text="IP address used during the most recent login.",
    )

    # ---- Layer 3 Hook: Multi-Tenancy ----
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text="Populated by Layer 3. Null = platform-level user.",
    )

    # ---- Audit Trail ----
    created_by = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Created By"),
        help_text="UUID of the user who created this record.",
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Updated By"),
        help_text="UUID of the user who last modified this record.",
    )

    # ---- Manager ----
    objects = KavanUserManager()
    active_objects = ActiveUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "iam_users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
            models.Index(fields=["status"], name="idx_user_status"),
            models.Index(fields=["tenant_id"], name="idx_user_tenant"),
            models.Index(fields=["created_at"], name="idx_user_created"),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"

    # ---- Computed Properties ----

    @property
    def full_name(self) -> str:
        """Return first + last name, falling back to email."""
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email

    @property
    def is_locked(self) -> bool:
        """True if the account is currently locked."""
        if self.status == UserStatus.LOCKED:
            if self.locked_until and timezone.now() < self.locked_until:
                return True
        return False

    @property
    def is_fully_active(self) -> bool:
        """True only when status is ACTIVE (not just is_active flag)."""
        return self.status == UserStatus.ACTIVE


# ============================================================
# REFRESH TOKEN MODEL
# ============================================================


class RefreshToken(TimestampMixin):
    """
    Stores hashed refresh tokens for JWT rotation.

    The raw token is NEVER stored — only its SHA-256 hash.
    Revocation checks Redis first (fast), then this table.

    Each refresh token is bound to a specific user + device.
    Token rotation: old token revoked → new token issued.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        db_index=True,
        verbose_name=_("User"),
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Token Hash"),
        help_text="SHA-256 hash of the raw refresh token.",
    )
    device_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Device ID"),
        help_text="References TrustedDevice if device is registered.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address"),
        help_text="IP from which this token was issued.",
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
    )
    is_revoked = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Revoked"),
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expires At"),
        help_text="Absolute expiry — 30 days from issue time.",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Revoked At"),
    )

    class Meta:
        db_table = "iam_refresh_tokens"
        verbose_name = _("Refresh Token")
        verbose_name_plural = _("Refresh Tokens")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_revoked"], name="idx_rt_user_active"),
            models.Index(fields=["expires_at"], name="idx_rt_expires"),
        ]

    def __str__(self) -> str:
        return f"RefreshToken({self.user.email}, revoked={self.is_revoked})"


# ============================================================
# EMAIL VERIFICATION MODEL
# ============================================================


class EmailVerification(models.Model):
    """
    Tracks email verification tokens sent to users.

    The raw token is never stored — only its SHA-256 hash.
    One token per user at a time; old tokens are invalidated on
    resend.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="email_verifications",
        verbose_name=_("User"),
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Token Hash"),
        help_text="SHA-256 hash of the verification token.",
    )
    email = models.EmailField(
        verbose_name=_("Email"),
        help_text="The email address being verified.",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_("Is Used"),
        help_text="True once the user has consumed this token.",
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expires At"),
        help_text="24 hours from creation time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iam_email_verifications"
        verbose_name = _("Email Verification")
        verbose_name_plural = _("Email Verifications")
        indexes = [
            models.Index(fields=["user", "is_used"], name="idx_ev_user_used"),
        ]

    def __str__(self) -> str:
        return f"EmailVerification({self.email}, used={self.is_used})"


# ============================================================
# PASSWORD RESET MODEL
# ============================================================


class PasswordReset(models.Model):
    """
    Tracks password reset tokens.

    Security:
      - Raw token is NEVER stored (SHA-256 hash only)
      - Token expires in 1 hour
      - Single-use: is_used=True after consumption
      - IP recorded for audit trail
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="password_resets",
        verbose_name=_("User"),
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Token Hash"),
        help_text="SHA-256 hash of the reset token.",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_("Is Used"),
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expires At"),
        help_text="1 hour from creation time.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Requested From IP"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iam_password_resets"
        verbose_name = _("Password Reset")
        verbose_name_plural = _("Password Resets")
        indexes = [
            models.Index(fields=["user", "is_used"], name="idx_pr_user_used"),
            models.Index(fields=["expires_at"], name="idx_pr_expires"),
        ]

    def __str__(self) -> str:
        return f"PasswordReset({self.user.email}, used={self.is_used})"


# ============================================================
# SERVICE ACCOUNT MODEL (Layer 2 stub — full impl in Layer 8)
# ============================================================


class ServiceAccount(TimestampMixin):
    """
    Machine identity for non-human API consumers.

    Examples:
      - KAVAN Agent (Layer 8)
      - Internal Scheduler
      - Marketplace integrations (Layer 6)
      - Billing Daemon (Layer 9)

    LAYER 2 STATUS: Model stub only.
    Full API key issuance and service JWT flow: Layer 8.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Service Name"),
        help_text='e.g. "kavan-agent", "billing-daemon"',
    )
    api_key_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("API Key Hash"),
        help_text="SHA-256 hash of the raw API key. Raw key shown once at creation.",
    )
    scopes = models.JSONField(
        default=list,
        verbose_name=_("Scopes"),
        help_text='e.g. ["audit:read", "session:revoke"]',
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Used At"),
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text="Null = no expiry.",
    )
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text="Layer 3 hook.",
    )

    class Meta:
        db_table = "iam_service_accounts"
        verbose_name = _("Service Account")
        verbose_name_plural = _("Service Accounts")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"ServiceAccount({self.name})"
