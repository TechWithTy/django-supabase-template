from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.core.cache import cache
import time
import logging
from django.http import HttpResponse
from apps.caching.utils.redis_cache import get_or_set_cache

logger = logging.getLogger(__name__)


@cache_page(60 * 15)  # Cache for 15 minutes
def cached_template_view(request):
    """
    Example view that caches the entire rendered template.
    
    This demonstrates Django's built-in template caching using the cache_page decorator.
    It's useful for pages that are expensive to render but don't change frequently.
    """
    # Simulate expensive data gathering and processing
    logger.info("Gathering data for template rendering")
    time.sleep(1)  # Simulate slow operation
    
    context = {
        'title': 'Cached Template Example',
        'items': [
            {'name': 'Item 1', 'value': 100},
            {'name': 'Item 2', 'value': 200},
            {'name': 'Item 3', 'value': 300},
        ],
        'timestamp': time.time(),
    }
    
    # In a real app, this would render an actual template
    # return render(request, 'example_template.html', context)
    
    # For this example, we'll just return a string
    html = f"<html><body><h1>{context['title']}</h1><p>Time: {context['timestamp']}</p></body></html>"
    return HttpResponse(html)


def cached_template_fragment(request):
    """
    Example view that demonstrates caching template fragments.
    
    This is useful when only parts of a page are expensive to render
    or when different parts of the page have different cache requirements.
    """
    # Get the current user for personalization
    user_id = getattr(request.user, 'id', None) or 'anonymous'
    
    # Get or compute expensive parts that can be cached
    def get_expensive_fragment():
        logger.info("Computing expensive template fragment")
        time.sleep(1.5)  # Simulate slow operation
        
        # In a real app, this might be complex HTML from a template fragment
        return "<div class='expensive-fragment'>This part was expensive to render</div>"
    
    # Cache the expensive fragment for 1 hour
    expensive_fragment = get_or_set_cache(
        f"template_fragment:expensive:{user_id}",
        get_expensive_fragment,
        timeout=60*60
    )
    
    # Get personalized content that shouldn't be cached
    personalized_content = f"<div>Hello, User {user_id}! Current time: {time.time()}</div>"
    
    # Combine cached and non-cached parts
    html = f"""<html>
    <body>
        <h1>Template Fragment Caching Example</h1>
        {personalized_content}
        {expensive_fragment}
        <p>This page combines cached and non-cached content.</p>
    </body>
    </html>"""
    
    from django.http import HttpResponse
    return HttpResponse(html)


def versioned_template_caching(request):
    """
    Example view that demonstrates versioned template caching.
    
    This is useful when you need to invalidate all cached templates
    when the template design changes.
    """
    # Get the current template version from cache or settings
    template_version = cache.get('template_version', 'v1')
    
    # Create a cache key that includes the template version
    cache_key = f"versioned_template:{template_version}:example"
    
    def render_template():
        logger.info("Rendering template with version {template_version}")
        time.sleep(1)  # Simulate slow rendering
        
        # In a real app, this would render an actual template
        return f"<html><body><h1>Versioned Template (v{template_version})</h1><p>Time: {time.time()}</p></body></html>"
    
    # Get from cache or render and cache for 1 day
    html = get_or_set_cache(cache_key, render_template, timeout=60*60*24)
    
    from django.http import HttpResponse
    return HttpResponse(html)


def invalidate_template_cache(request):
    """
    Example view that invalidates all cached templates by updating the template version.
    
    This demonstrates how to invalidate all cached templates at once
    when the template design changes.
    """
    # Get the current template version
    current_version = cache.get('template_version', 'v1')
    
    # Increment the version
    if current_version.startswith('v'):
        try:
            version_num = int(current_version[1:])
            new_version = f"v{version_num + 1}"
        except ValueError:
            new_version = 'v2'
    else:
        new_version = 'v2'
    
    # Update the template version in cache
    cache.set('template_version', new_version, timeout=None)  # No expiration
    
    from django.http import HttpResponse
    return HttpResponse(f"Template cache invalidated. New version: {new_version}")
