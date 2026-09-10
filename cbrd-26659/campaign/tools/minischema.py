"""Minimal JSON Schema (draft 2020-12 subset) validator with no third-party dependency.

Supports the subset the campaign schemas use: type (single or list), properties,
required, additionalProperties (bool or schema), enum, const, items, minItems,
maxItems, uniqueItems, pattern, minimum, maximum, minLength, allOf, anyOf, oneOf,
not, if/then/else, and same-document $ref (``#/$defs/...``). Anything else is
ignored, so a schema that relies on an unsupported keyword must not be trusted
here; run it through a full validator (``python3 -m jsonschema``) instead.
"""
import re

#: Keywords this module evaluates. Anything else in a schema is a silent no-op.
EVALUATED_KEYWORDS = frozenset({
    "$ref", "type", "enum", "const", "pattern", "minLength", "minimum", "maximum",
    "properties", "required", "additionalProperties", "propertyNames",
    "items", "minItems", "maxItems", "uniqueItems",
    "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
})
#: Keywords that carry no constraint, so ignoring them is correct.
ANNOTATION_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$comment", "title", "description", "default", "examples",
})

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def resolve_ref(root, ref):
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref!r}; only same-document refs are supported")
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[part]
    return node


def validate(instance, schema, root=None, path="$"):
    """Return a list of human-readable error strings (empty when valid)."""
    if root is None:
        root = schema
    errors = []
    if schema is True:
        return errors
    if schema is False:
        return [f"{path}: schema forbids any value"]

    if "$ref" in schema:
        errors.extend(validate(instance, resolve_ref(root, schema["$ref"]), root, path))

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        unknown = [t for t in types if t not in _TYPE_CHECKS]
        if unknown:
            raise ValueError(f"unknown type name(s) {unknown!r} at {path}")
        if not any(_TYPE_CHECKS[t](instance) for t in types):
            errors.append(f"{path}: expected type {'/'.join(types)}, got {type(instance).__name__}")
            return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']!r}")
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value {instance!r} != const {schema['const']!r}")

    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], root, f"{path}.{key}"))
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}: unexpected property {key!r}")
                elif isinstance(extra, dict):
                    errors.extend(validate(value, extra, root, f"{path}.{key}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = []
            for item in instance:
                if item in seen:
                    errors.append(f"{path}: duplicate item {item!r}")
                seen.append(item)
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{i}]"))

    for sub in schema.get("allOf", []):
        errors.extend(validate(instance, sub, root, path))
    if "anyOf" in schema:
        if not any(not validate(instance, sub, root, path) for sub in schema["anyOf"]):
            errors.append(f"{path}: value matches none of anyOf")
    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if not validate(instance, sub, root, path))
        if matches != 1:
            errors.append(f"{path}: value matches {matches} of oneOf alternatives, expected exactly 1")
    if "not" in schema and not validate(instance, schema["not"], root, path):
        errors.append(f"{path}: value matches forbidden schema")
    if "if" in schema:
        if not validate(instance, schema["if"], root, path):
            if "then" in schema:
                errors.extend(validate(instance, schema["then"], root, path))
        elif "else" in schema:
            errors.extend(validate(instance, schema["else"], root, path))
    return errors


def unsupported_keywords(schema, path="$"):
    """Return [(path, keyword)] for every keyword this module would ignore.

    A non-empty result means validation against that schema is not trustworthy:
    the ignored keyword's constraint would never be applied.
    """
    found = []
    if not isinstance(schema, dict):
        return found
    for key, value in schema.items():
        if key in ANNOTATION_KEYWORDS:
            if key == "$defs" and isinstance(value, dict):
                for name, sub in value.items():
                    found += unsupported_keywords(sub, f"{path}.$defs.{name}")
            continue
        if key not in EVALUATED_KEYWORDS:
            found.append((path, key))
            continue
        if key in ("properties", "propertyNames"):
            if isinstance(value, dict) and key == "properties":
                for name, sub in value.items():
                    found += unsupported_keywords(sub, f"{path}.{name}")
            else:
                found += unsupported_keywords(value, f"{path}.{key}")
        elif key in ("items", "additionalProperties", "not", "if", "then", "else"):
            found += unsupported_keywords(value, f"{path}.{key}")
        elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
            for i, sub in enumerate(value):
                found += unsupported_keywords(sub, f"{path}.{key}[{i}]")
    return found
