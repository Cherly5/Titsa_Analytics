import sys

from google.protobuf.descriptor import FieldDescriptor

from feedScript import save_feed_as_json, fetch_and_parse_feed

def get_field_type_name(field_descriptor):
    """Devuelve el nombre legible del tipo de un campo protobuf."""
    type_map = {
        FieldDescriptor.TYPE_DOUBLE: "double",
        FieldDescriptor.TYPE_FLOAT: "float",
        FieldDescriptor.TYPE_INT64: "int64",
        FieldDescriptor.TYPE_UINT64: "uint64",
        FieldDescriptor.TYPE_INT32: "int32",
        FieldDescriptor.TYPE_FIXED64: "fixed64",
        FieldDescriptor.TYPE_FIXED32: "fixed32",
        FieldDescriptor.TYPE_BOOL: "bool",
        FieldDescriptor.TYPE_STRING: "string",
        FieldDescriptor.TYPE_GROUP: "group",
        FieldDescriptor.TYPE_MESSAGE: "message",
        FieldDescriptor.TYPE_BYTES: "bytes",
        FieldDescriptor.TYPE_UINT32: "uint32",
        FieldDescriptor.TYPE_ENUM: "enum",
        FieldDescriptor.TYPE_SFIXED32: "sfixed32",
        FieldDescriptor.TYPE_SFIXED64: "sfixed64",
        FieldDescriptor.TYPE_SINT32: "sint32",
        FieldDescriptor.TYPE_SINT64: "sint64",
    }
    return type_map.get(field_descriptor.type, "unknown")


def describe_message(message, schema, max_depth=10, current_depth=0):
    """
    Rellena el diccionario 'scheme' con la estructura del mensaje protobuf.
    'scheme' debe ser un diccionario mutable (se modificará in-place).
    """
    if current_depth > max_depth:
        return
    descriptor = message.DESCRIPTOR
    for field in descriptor.fields:
        field_name = field.name
        # Si el campo es repetido, se indica "repeated" y el tipo del elemento
        if field.label == FieldDescriptor.LABEL_REPEATED:
            # Para describir el tipo interno, se comprueba si el mensaje tiene elementos en ese campo (si es un mensaje anidado)
            # Si el mensaje tiene al menos un elemento, se toma uno como muestra
            if len(getattr(message, field_name)) > 0:
                element = getattr(message, field_name)[0]
                if field.type == FieldDescriptor.TYPE_MESSAGE:
                    inner_schema = {}
                    describe_message(element, inner_schema, max_depth, current_depth + 1)
                    field_schema = {
                        "type": "repeated",
                        "items": inner_schema
                    }
                else:
                    field_schema = {
                        "type": "repeated",
                        "items_type": get_field_type_name(field)
                    }
            else:
                # Sin elementos, solo se puede describir el tipo de campo, pero no su estructura interna
                if field.type == FieldDescriptor.TYPE_MESSAGE:
                    field_schema = {
                        "type": "repeated",
                        "items": {"type": "message", "message_type": field.message_type.name}
                    }
                else:
                    field_schema = {
                        "type": "repeated",
                        "items_type": get_field_type_name(field)
                    }
        else:
            # Campo singular
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                field_schema = {}
                # Si el mensaje tiene el campo presente, se describe su estructura interna
                if message.HasField(field_name):
                    sub_msg = getattr(message, field_name)
                    describe_message(sub_msg, field_schema, max_depth, current_depth + 1)
                else:
                    field_schema["type"] = "message"
                    field_schema["message_type"] = field.message_type.name
            elif field.type == FieldDescriptor.TYPE_ENUM:
                # Extraer los valores del enum (nombre y número)
                enum_values = {}
                for val in field.enum_type.values:
                    enum_values[val.name] = val.number
                field_schema = {
                    "type": "enum",
                    "values": enum_values
                }
            else:
                field_schema = {"type": get_field_type_name(field)}
        schema[field_name] = field_schema


def generate_schema_from_feed(feed):
    """
    A partir de un FeedMessage, genera un esquema combinado para las entidades.
    Retorna un diccionario con 'header' y 'entity_types'.
    """
    schema = {"header": {}, "entity_types": {}}
    describe_message(feed.header, schema["header"])

    entity_schemas = {}
    for entity in feed.entity:
        # ListFields devuelve solo los campos que tienen valor
        for field_descriptor, value in entity.ListFields():
            field_name = field_descriptor.name
            # Se filtran los campos que son los tipos de entidad relevantes
            if field_name in ('trip_update', 'vehicle', 'alert', 'shape', 'stop', 'trip_modifications'):
                if field_name not in entity_schemas:
                    entity_schemas[field_name] = {}
                describe_message(value, entity_schemas[field_name])
    schema["entity_types"] = entity_schemas
    return schema

def main(feed_url, output_schema_json):
    print(f"Descargando feed desde: {feed_url}")
    feed = fetch_and_parse_feed(feed_url)
    print("Generando esquema...")
    schema = generate_schema_from_feed(feed)
    save_feed_as_json(schema, output_schema_json)
    print(f"Esquema guardado en: {output_schema_json}")
    print("Tipos de entidades presentes:", list(schema["entity_types"].keys()))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python feedSchemaScript.py <URL_feed> <salida_script.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])