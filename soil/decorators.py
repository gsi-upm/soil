def report(f: property):
    if isinstance(f, property):
        setattr(f.fget, "add_to_report", True)
    else:
        setattr(f, "add_to_report", True)
    return f