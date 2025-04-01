🪳Fix Realtime Api Access 
🧪 Make sure  E2E tests  cleanup created and modified data 
🧪🪳   C:\Users\tyriq\AppData\Local\Programs\Python\Python312\Lib\site-packages\django\core\handlers\base.py:61: UserWarning: No directory at: C:\Users\tyriq\Documents\Github\django-supabase-template\backend\staticfiles\
    mw_instance = middleware(adapted_handler)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html 🧪🪳
📃 Update api documentation and make into swagger file
🗄️You have 20 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): admin, auth, authentication, contenttypes, sessions, users.
Run 'python manage.py migrate' to apply them.

🔐Insecure MD5 hash usage in multiple files:
redis_cache.py is using MD5 for hashing
database_view.py is using MD5 for cache keys and token hashing
client_view.py is using MD5 for path hashing
Potential SQL injection vulnerability:
In execute_query function in client_view.py
Allowing raw SQL queries without proper parameterization
Secrets exposure:
Returning Supabase URL and anon key in client_view.py
These are sensitive and should be handled more carefully🔐

🪳 https://github.com/supabase/realtime/issues/1111#issuecomment-2742384131

## Database Tables Needed
🧪 Update credit allocation test stripe and  user views to use real db to check for table

- `credits_credittransaction` - Table for storing credit transactions
- `users_userprofile` - Table for storing user profile information
- Test tables for database operations:
  - Create temporary test tables for database CRUD operations tests
  - Ensure proper schema permissions for test tables
- Ensure proper foreign key relationships between tables
- Consider adding row-level security (RLS) policies for multi-tenancy

## Tests That Need Updating When Credits Table is Created

1. `backend/apps/users/views/creditable_views/tests/test_creditable_views.py`
   - Current tests assume a mock credits system
   - Update fixture `user_with_credits` to use actual credits table
   - Modify credit deduction tests to verify actual transactions

2. `backend/apps/users/views/creditable_views/tests/test_creditable_views_edge_cases.py`
   - Update edge case tests to handle real credit transactions
   - Add cleanup to ensure test credits are removed after tests

3. `backend/apps/users/views/tests/test_database_views.py`
   - Currently uses generic test tables
   - Add specific tests for credits table operations
   - Ensure database router tests account for credits table

## Files to Update When Tables Are Created

### When creating `credits_credittransaction`:
- `backend/apps/users/models.py` - Add model definition
- `backend/apps/users/serializers.py` - Create serializer for the model
- `backend/apps/users/views/creditable_views/main_view.py` - Add endpoints to manage transactions
- `backend/apps/users/views/creditable_views/tests/test_creditable_views.py` - Add tests for transaction endpoints
- `backend/apps/users/admin.py` - Register model in Django admin
- Migration files will be generated with `python manage.py makemigrations`

### When creating `users_userprofile`:
- `backend/apps/users/models.py` - Add model definition
- `backend/apps/users/serializers.py` - Create serializer for the model
- `backend/apps/users/views/user_views.py` - Add endpoints to manage user profiles
- `backend/apps/users/views/tests/test_user_views.py` - Add tests for user profile endpoints
- `backend/apps/users/admin.py` - Register model in Django admin
- Migration files will be generated with `python manage.py makemigrations`

### SQL Scripts for Supabase
- Create SQL scripts to set up corresponding tables in Supabase
- Add RLS policies for each table in Supabase
- Set up triggers or functions for syncing data if needed

Notes:
https://www.reddit.com/r/Supabase/comments/165kbqs/is_supabase_capable_of_multi_tenancy/

https://www.reddit.com/r/Supabase/comments/1ace4ag/database_architecture_for_multitenant_apps/

https://www.reddit.com/r/Supabase/comments/1cb4blm/multitenant_database_design/

https://github.com/orgs/supabase/discussions/1615