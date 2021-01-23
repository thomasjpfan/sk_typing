import inspect
from ._extract import unpack_annotation
from ._extract import AnnotatedMeta


def _get_default(default):
    if isinstance(default, bool):
        return str(default)
    elif default is None:
        return "None"
    else:
        return default


def _is_instance(value, annotation):
    annotation_meta = unpack_annotation(annotation)
    if annotation_meta.class_name in {"bool", "int", "float", "str"}:
        return isinstance(value, annotation)
    elif annotation_meta.class_name == "Literal":
        for item in annotation_meta.args:
            if value == item:
                return True
        return False
    elif annotation_meta.class_name == "None":
        return value is None
    else:
        ValueError(f"Unsupported annotation: {annotation}")


def _process_builtins(name, annotation_meta):
    return {
        "type": "Hyperparameter",
        "name": name,
        "init_args": {
            "semantic_types": [name],
            "_structural_type": annotation_meta.class_name,
        },
    }


def _process_literal(name, annotation_meta):
    values = list(annotation_meta.args)
    if len(values) == 1:
        # Literal are all strings
        new_meta = AnnotatedMeta(
            class_name=type(values[0]).__name__, args=(), metadata=()
        )
        return _process_constant(name, new_meta)

    return {
        "type": "Enumeration",
        "name": name,
        "init_args": {
            "semantic_types": [name],
            "values": values,
            "_structural_type": "str",
        },
    }


def _process_constant(name, annotation_meta):
    return {
        "type": "Constant",
        "name": name,
        "init_args": {
            "semantic_types": [name],
            "_structural_type": annotation_meta.class_name,
        },
    }


def _process_union(name, annotation_meta, default=inspect.Parameter.empty):
    output = {"name": name, "type": "Union", "init_args": {"semantic_types": [name]}}

    hyperparams = []

    normalized_default = ""

    for sub_annotation in annotation_meta.args:
        sub_output = get_d3m_representation(name, sub_annotation)
        sub_type = sub_output["init_args"]["_structural_type"]
        sub_name = f"{name}__{sub_type}"
        sub_output["name"] = sub_name
        if (
            not normalized_default
            and default != inspect.Parameter.empty
            and _is_instance(default, sub_annotation)
        ):
            normalized_default = sub_name
            sub_output["init_args"]["default"] = _get_default(default)
        hyperparams.append(sub_output)

    output["hyperparams"] = hyperparams

    if normalized_default:
        default = normalized_default

    return output, default


def get_d3m_representation(
    name, annotation, description="", default=inspect.Parameter.empty
):
    annotation_meta = unpack_annotation(annotation)

    if annotation_meta.class_name not in {
        "bool",
        "int",
        "float",
        "str",
        "Literal",
        "None",
        "Union",
    }:
        raise ValueError(f"Unsupported class_name: {annotation_meta.class_name}")

    if annotation_meta.class_name in {"bool", "int", "float", "str"}:
        output = _process_builtins(
            name,
            annotation_meta=annotation_meta,
        )
    elif annotation_meta.class_name == "None":
        output = _process_constant(name, annotation_meta=annotation_meta)
    elif annotation_meta.class_name == "Union":
        output, default = _process_union(
            name, annotation_meta=annotation_meta, default=default
        )
    else:  # Literal
        output = _process_literal(
            name,
            annotation_meta=annotation_meta,
        )

    if default != inspect.Parameter.empty:
        output["init_args"]["default"] = _get_default(default)
    if description:
        output["init_args"]["description"] = description

    return output
