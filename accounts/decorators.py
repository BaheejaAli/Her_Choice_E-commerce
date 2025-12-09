from functools import wraps
from django.shortcuts import redirect

def logout_required(redirect_to='home'):
    """
    Redirects authenticated users to `redirect_to` page.
    If the user is not authenticated, they can access the view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request,*args,**kwargs):
            if request.user.is_authenticated:
                return redirect(redirect_to)
            return view_func(request,*args, **kwargs)
        return _wrapped_view
    return decorator