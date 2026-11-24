"""Celery's ``shared_task`` when Celery is installed; otherwise the same decorator API
that runs tasks inline. Task modules import from here so their logic can be
called and tested directly in any environment.
"""
try:
    from celery import shared_task
    CELERY_INSTALLED = True
except ImportError:  # Celery not installed: run tasks in-process
    CELERY_INSTALLED = False

    def shared_task(*decorator_args, **decorator_options):
        def decorate(func):
            def delay(*args, **kwargs):
                return func(*args, **kwargs)

            def apply_async(args=(), kwargs=None, **options):
                return func(*args, **(kwargs or {}))

            func.delay = delay
            func.apply_async = apply_async
            return func

        if len(decorator_args) == 1 and callable(decorator_args[0]) and not decorator_options:
            return decorate(decorator_args[0])
        return decorate
