def fallback(processors, fallback):
    def fallback_spec(fieldfile, context):
        context.fallback = fallback
        context.processors = processors

    return fallback_spec
