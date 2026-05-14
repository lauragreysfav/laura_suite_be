SCHEMAS = [
    {
        "name": "stashdb_performers",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "aliases", "type": "string[]", "optional": True},
            {"name": "image_url", "type": "string", "optional": True},
            {"name": "gender", "type": "string", "optional": True},
            {"name": "birthdate", "type": "string", "optional": True},
            {"name": "scene_count", "type": "int32"},
        ],
        "default_sorting_field": "scene_count",
    },
    {
        "name": "stashdb_studios",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "image_url", "type": "string", "optional": True},
            {"name": "scene_count", "type": "int32"},
        ],
        "default_sorting_field": "scene_count",
    },
    {
        "name": "stashdb_scenes",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "details", "type": "string", "optional": True},
            {"name": "release_date", "type": "string", "optional": True},
            {"name": "duration", "type": "int32", "optional": True},
            {"name": "studio_name", "type": "string", "optional": True},
            {"name": "performer_names", "type": "string[]", "optional": True},
            {"name": "tags", "type": "string[]", "optional": True},
            {"name": "fingerprints", "type": "string[]", "optional": True},
            {"name": "images", "type": "string[]", "optional": True},
        ],
    },
]
