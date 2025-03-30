from django.contrib import admin
from .models import StripeCustomer, StripeSubscription, StripePlan

@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'customer_id', 'livemode', 'created_at')
    search_fields = ('user__username', 'user__email', 'customer_id')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        # Only allow creating new customer records, not editing
        if obj:
            return self.readonly_fields + ('user', 'customer_id', 'livemode')
        return self.readonly_fields


@admin.register(StripePlan)
class StripePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_id', 'amount_display', 'interval', 'initial_credits', 'monthly_credits', 'active')
    list_filter = ('active', 'livemode', 'interval')
    search_fields = ('name', 'plan_id')
    readonly_fields = ('created_at', 'updated_at')
    
    def amount_display(self, obj):
        return f"{obj.currency.upper()} {obj.amount/100:.2f}"
    amount_display.short_description = 'Amount'


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_id', 'status', 'plan_display', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('status', 'cancel_at_period_end', 'livemode')
    search_fields = ('user__username', 'user__email', 'subscription_id', 'plan_id')
    readonly_fields = ('created_at', 'updated_at')
    
    def plan_display(self, obj):
        try:
            plan = StripePlan.objects.get(plan_id=obj.plan_id)
            return plan.name
        except StripePlan.DoesNotExist:
            return obj.plan_id
    plan_display.short_description = 'Plan'
