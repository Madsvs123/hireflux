from django.contrib import admin

from apps.organizations.models import (
    Department,
    HiringTeam,
    HiringTeamMember,
    Office,
    Organization,
)


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ("name", "parent", "is_active")
    show_change_link = True


class OfficeInline(admin.TabularInline):
    model = Office
    extra = 0
    fields = ("name", "city", "country", "is_headquarters", "is_active")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "org_type", "industry", "is_active", "created_at")
    list_filter = ("org_type", "is_active", "industry")
    search_fields = ("name", "slug", "webiste")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [DepartmentInline, OfficeInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "parent", "is_active")
    list_filter = ("is_active", "organization")
    search_fields = ("name",)
    raw_id_fields = ("organization", "parent")


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "city", "country", "is_headquarters", "is_active")
    list_filter = ("is_active", "is_headquarters", "country")
    search_fields = ("name", "city")
    raw_id_fields = ("organization",)


class HiringTeamMemberInline(admin.TabularInline):
    model = HiringTeamMember
    extra = 0
    raw_id_fields = ("user",)


@admin.register(HiringTeam)
class HiringTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "department", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    raw_id_fields = ("organization", "department")
    inlines = [HiringTeamMemberInline]


@admin.register(HiringTeamMember)
class HiringTeamMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "role", "is_active")
    list_filter = ("role", "is_active")
    raw_id_fields = ("user", "team")
