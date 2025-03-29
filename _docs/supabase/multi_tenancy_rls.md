# Multi-Tenancy Implementation with Supabase Row-Level Security (RLS)

## Overview

This document outlines how to implement multi-tenancy in the Django-Supabase template using Supabase's Row-Level Security (RLS) policies. This approach allows multiple tenants to share a single database while ensuring data isolation through PostgreSQL's security features.

## Table of Contents

1. [Introduction to Multi-Tenancy](#introduction-to-multi-tenancy)
2. [Row-Level Security Approach](#row-level-security-approach)
3. [Implementation Steps](#implementation-steps)
4. [Django Integration](#django-integration)
5. [Testing and Validation](#testing-and-validation)
6. [Performance Considerations](#performance-considerations)
7. [Security Best Practices](#security-best-practices)

## Introduction to Multi-Tenancy

Multi-tenancy refers to an architecture where a single instance of software serves multiple tenants (organizations or users). Each tenant's data is isolated from other tenants, even though they share the same database and application.

In the context of the Django-Supabase template, multi-tenancy allows:

- SaaS applications to serve multiple organizations
- B2B platforms to isolate client data
- Marketplace applications where vendors need data separation

## Row-Level Security Approach

Row-Level Security (RLS) in Supabase leverages PostgreSQL's built-in security policies to filter rows based on the authenticated user's properties. This is the simplest multi-tenancy approach with these characteristics:

### Advantages

- **Single Database**: All tenants share the same tables and schemas
- **Native Security**: Uses Supabase's security model as designed
- **Simplified Infrastructure**: No need for complex database sharding or routing
- **Seamless Scaling**: Works well for small to medium-sized applications

### Limitations

- **Shared Resources**: All tenants share the same database resources
- **Policy Complexity**: As data models grow, policies can become complex
- **Performance at Scale**: May experience degradation with many tenants and large datasets
- **Human Error Risk**: Incorrect policy implementation can lead to data leaks

## Implementation Steps

### 1. Database Schema Changes

First, add a `tenant_id` field to all tables that should be tenant-specific:

```sql
-- For existing tables
ALTER TABLE your_table ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- Create a tenants table if it doesn't exist
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ
);
```

### 2. Create RLS Policies

For each tenant-specific table, create RLS policies that filter rows based on the tenant ID stored in the JWT token:

```sql
-- Enable RLS on the table
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- Create a policy for SELECT operations
CREATE POLICY tenant_isolation_select ON your_table 
  FOR SELECT USING (tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id');

-- Create a policy for INSERT operations
CREATE POLICY tenant_isolation_insert ON your_table 
  FOR INSERT WITH CHECK (tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id');

-- Create a policy for UPDATE operations
CREATE POLICY tenant_isolation_update ON your_table 
  FOR UPDATE USING (tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id');

-- Create a policy for DELETE operations
CREATE POLICY tenant_isolation_delete ON your_table 
  FOR DELETE USING (tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id');
```

### 3. Add Tenant Information to Authentication

When a user signs up or logs in, you need to include tenant information in their JWT token:

```sql
-- Add custom claims to the JWT token during sign-up or sign-in
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Assuming user's email domain or explicit tenant selection determines their tenant
  -- This is just an example - you'll need to adapt to your tenant assignment logic
  UPDATE auth.users
  SET raw_app_meta_data = jsonb_set(
    raw_app_meta_data,
    '{tenant_id}',
    '"' || (SELECT id FROM tenants WHERE domain = split_part(NEW.email, '@', 2)) || '"'
  )
  WHERE id = NEW.id;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger the function after a new user signs up
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

## Django Integration

### 1. Tenant Model

Create a Tenant model in Django:

```python
# apps/tenants/models.py
from django.db import models
import uuid

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
```

### 2. User-Tenant Association

Update the UserProfile model to include tenant information:

```python
# apps/users/models.py
from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    # ... existing fields
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True)
    
    # ... existing methods
```

### 3. Supabase JWT Integration

Modify the authentication process to include tenant information in the JWT token:

```python
# apps/authentication/services.py
from supabase import create_client
from django.conf import settings

def get_supabase_client(user):
    """Create a Supabase client with tenant information in the JWT."""
    # Get tenant_id from user's profile
    tenant_id = str(user.profile.tenant.id) if user.profile.tenant else None
    
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_KEY,
        options={
            "auth": {
                "persistSession": False,
                "autoRefreshToken": False,
            }
        }
    ).auth.sign_in_with_password(
        {"email": user.email, "password": "dummy-not-used"},
        {"tenant_id": tenant_id}  # Add tenant_id to JWT metadata
    )
```

### 4. Middleware for Tenant Context

Create middleware to ensure tenant context is maintained throughout requests:

```python
# apps/tenants/middleware.py
from django.utils.functional import SimpleLazyObject
from .models import Tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for unauthenticated users or paths that don't need tenant context
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Set tenant on the request
        request.tenant = SimpleLazyObject(lambda: self._get_tenant(request))
        
        # Set a thread-local tenant for background processes
        from threading import local
        _thread_locals = local()
        _thread_locals.tenant = request.tenant
        
        response = self.get_response(request)
        return response
        
    def _get_tenant(self, request):
        # Get tenant from user profile
        return request.user.profile.tenant
```

### 5. Automatic Tenant Assignment

Ensure all database operations include the tenant ID:

```python
# apps/tenants/models.py
from django.db import models

class TenantAwareModel(models.Model):
    """Base model that automatically sets the tenant ID."""
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    
    class Meta:
        abstract = True
        
    def save(self, *args, **kwargs):
        # Get current tenant from thread local or other context
        from threading import local
        _thread_locals = local()
        
        if not self.tenant_id and hasattr(_thread_locals, 'tenant'):
            self.tenant = _thread_locals.tenant
            
        super().save(*args, **kwargs)
```

## Testing and Validation

To test your multi-tenant implementation:

1. **Create Test Tenants**: Set up multiple tenants in your system

2. **Create Users**: Create users belonging to different tenants

3. **Cross-Tenant Data Access Tests**: Verify users from one tenant cannot access another tenant's data

```python
# Example test for tenant isolation
import pytest
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.your_app.models import YourModel

User = get_user_model()

@pytest.mark.django_db
class TestMultiTenancy:
    def test_tenant_isolation(self):
        # Create tenants
        tenant1 = Tenant.objects.create(name="Tenant 1")
        tenant2 = Tenant.objects.create(name="Tenant 2")
        
        # Create users
        user1 = User.objects.create_user(username="user1", password="password")
        user1.profile.tenant = tenant1
        user1.profile.save()
        
        user2 = User.objects.create_user(username="user2", password="password")
        user2.profile.tenant = tenant2
        user2.profile.save()
        
        # Create data for each tenant
        item1 = YourModel.objects.create(tenant=tenant1, name="Item 1")
        item2 = YourModel.objects.create(tenant=tenant2, name="Item 2")
        
        # Test isolation through Supabase client
        from apps.authentication.services import get_supabase_client
        
        client1 = get_supabase_client(user1)
        data1 = client1.table('your_table').select('*').execute()
        
        client2 = get_supabase_client(user2)
        data2 = client2.table('your_table').select('*').execute()
        
        # Verify user1 only sees tenant1's data
        assert len(data1.data) == 1
        assert data1.data[0]['name'] == "Item 1"
        
        # Verify user2 only sees tenant2's data
        assert len(data2.data) == 1
        assert data2.data[0]['name'] == "Item 2"
```

## Performance Considerations

As your multi-tenant application grows, consider these performance optimizations:

1. **Indexing**: Add indexes on tenant_id columns for improved query performance

```sql
CREATE INDEX idx_your_table_tenant_id ON your_table(tenant_id);
```

2. **Partitioning**: For very large tables, consider PostgreSQL table partitioning by tenant_id

```sql
CREATE TABLE your_table (id SERIAL, tenant_id UUID, data TEXT) PARTITION BY LIST (tenant_id);
```

3. **Query Optimization**: Ensure all queries include tenant_id filters, even if RLS would apply them anyway

4. **Monitoring**: Set up monitoring for query performance by tenant to identify problematic tenants

## Security Best Practices

### 1. Validate RLS Policies

Regularly test your RLS policies to ensure they're working correctly:

```sql
-- Test as a specific tenant
SELECT set_config('request.jwt.claims', '{"app_metadata":{"tenant_id":"YOUR-TENANT-UUID"}}', true);

-- Try to access data
SELECT * FROM your_table LIMIT 10;
```

### 2. Admin Access

Create a separate policy for administrators who need cross-tenant access:

```sql
CREATE POLICY admin_access ON your_table
  FOR ALL
  USING (
    (auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
    OR tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id'
  );
```

### 3. Regular Audits

Implement audit logging for sensitive operations:

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID,
  action TEXT,
  table_name TEXT,
  record_id TEXT,
  old_data JSONB,
  new_data JSONB,
  timestamp TIMESTAMPTZ DEFAULT now()
);

-- Create a trigger function for auditing
CREATE OR REPLACE FUNCTION audit_changes()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_logs (tenant_id, user_id, action, table_name, record_id, old_data, new_data)
  VALUES (
    COALESCE(NEW.tenant_id, OLD.tenant_id),
    (auth.jwt() ->> 'sub')::UUID,
    TG_OP,
    TG_TABLE_NAME,
    CASE TG_OP
      WHEN 'DELETE' THEN OLD.id::TEXT
      ELSE NEW.id::TEXT
    END,
    CASE WHEN TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
    CASE WHEN TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN row_to_json(NEW) ELSE NULL END
  );
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## Conclusion

Implementing multi-tenancy with Supabase Row-Level Security provides a straightforward approach to data isolation in a shared database environment. This method works well for small to medium-sized applications and can scale reasonably well with proper indexing and query optimization.

As your application grows, you might consider more advanced multi-tenancy models such as schema-per-tenant or database-per-tenant, but the RLS approach provides an excellent starting point that balances simplicity, security, and performance.
