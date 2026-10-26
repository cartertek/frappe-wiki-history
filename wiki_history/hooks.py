app_name = "wiki_history"
app_title = "Wiki History"
app_publisher = "Cartertek LLC"
app_description = "Wikipedia-style page history for Frappe Wiki v3"
app_email = "admin@cartertek.ai"
app_license = "MIT"

required_apps = ["wiki"]
after_request = ["wiki_history.integration.inject_history_link"]
