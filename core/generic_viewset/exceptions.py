class SerializerIsNone(Exception):
    # Fix error serializer_class is None default in class
    # GenericViewSetCustom solven error set class
    # serializer default --> serializer_class = ExampleSerializerClass

    def __init__(self, *args):
        super().__init__(*args, "Atrribute serializer_class is None")


class ServiceIsNone(Exception):
    # Fix error service_controller_class is None default in class
    # GenericViewSetCustom solven error set class
    # serializer default --> service_controller_class = ExampleServiceController Class

    def __init__(self, *args):
        super().__init__(*args, "Atrribute service_controller_class is None")
