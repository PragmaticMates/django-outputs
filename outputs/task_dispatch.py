def dispatch_task(task_func, *args, **kwargs):
    """
    Dispatch a task using the first supported async API.
    """
    enqueue = getattr(task_func, "enqueue", None)
    if callable(enqueue):
        return enqueue(*args, **kwargs)

    apply_async = getattr(task_func, "apply_async", None)
    if callable(apply_async):
        return apply_async(args=args, kwargs=kwargs)

    delay = getattr(task_func, "delay", None)
    if callable(delay):
        return delay(*args, **kwargs)

    return task_func(*args, **kwargs)
