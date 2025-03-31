🪳Fix Realtime Api Access 
🧪 Make sure  E2E tests  cleanup created and modified data 
🧪🪳   C:\Users\tyriq\AppData\Local\Programs\Python\Python312\Lib\site-packages\django\core\handlers\base.py:61: UserWarning: No directory at: C:\Users\tyriq\Documents\Github\django-supabase-template\backend\staticfiles\
    mw_instance = middleware(adapted_handler)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html 🧪🐛

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

Notes:
https://www.reddit.com/r/Supabase/comments/165kbqs/is_supabase_capable_of_multi_tenancy/

https://www.reddit.com/r/Supabase/comments/1ace4ag/database_architecture_for_multitenant_apps/

https://www.reddit.com/r/Supabase/comments/1cb4blm/multitenant_database_design/

https://github.com/orgs/supabase/discussions/1615