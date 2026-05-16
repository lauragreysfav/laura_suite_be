# FileMonitor development config override
# Configured for LauraSuite Docker setup
config_dev = {
    "dockers": [
        {
            "GQL": "http://localhost:9999",
            "apiKey": "",
            "bindMounts": [
                {"D:\\LauraMedia": "/data/lauramedia"},
            ],
        },
    ],
}
