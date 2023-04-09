def report(f: property):
    print(f.fget)
    setattr(f.fget, "add_to_report", True)
    return f