# Importing necessary libraries
import re
import requests
from asksageclient import AskSageClient
import os

# TO CHANGE
project_id = 'PVT_kwHOAFWqhs4ASKOm'

system_prompt = """You are Sage, an AI chatbot created by Ask Sage.
When you write software code, you provide a description statement, followed by the indented code with detailed comments wrapped by ``` elements. 
You are a software developer with decades of experience, your responsibility is to write code that is not only efficient and reliable but also secure and meets the highest security standards such as the NIST Cybersecurity Framework and NIST Risk Management Framework. You must pay close attention to various types of injections, such as SQL injections and XSS injections, and ensure that code is free from vulnerabilities. Proper static and dynamic code security scanning and code review are essential to ensuring the security of the code. You are able to understand the requirements of a project and create code that meets those requirements. You must also be able to debug and troubleshoot any issues that arise. You always review your own code to ensure that it meets the highest security standards. Your purpose is to help government teams drive outcomes by providing them with secure and reliable software solutions that comply with specific security standards and protect against potential threats."""

def handle_item(cur_item):
    id = cur_item['id']
    title = cur_item['content']['title']
    body = cur_item['content']['body']
    for field_item in cur_item['fieldValues']['nodes']:
        field_name = field_item['field']['name']
        field_value = None
        if 'name' in field_item:
            field_value = field_item['name']
        if field_name == 'RC' and field_value == 'Yes':             
            return {'id': id, 'title': title, 'body': body}
    return None

def get_github_project_items():
    # Your GitHub token
    token = os.environ.get("github_token", None)

    # Define the headers for the request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Initial query
    query = """
    {
    node(id: \"""" + project_id + """\") { ... on ProjectV2 { items(first: 100) { pageInfo { endCursor hasNextPage } nodes{ id fieldValues(first: 8) { nodes{ ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon {  name }}} ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name }}}}} content{ ... on DraftIssue { title body } ...on Issue { title assignees(first: 10) { nodes{ login }}} ...on PullRequest { title assignees(first: 10) { nodes{ login }}}}}}}}}
    """

    count = 0
    res = []

    # Make the request
    response = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)

    # Print the response
    json_response = response.json()
    if json_response == None or 'data' not in json_response or 'node' not in json_response['data'] or 'items' not in json_response['data']['node'] or json_response['data']['node']['items']['nodes'] == None:
        print(json_response)
        return res
    
    for cur_item in json_response['data']['node']['items']['nodes']:
        new_item = handle_item(cur_item)
        if new_item != None:
            res.append(new_item)
        count = count + 1


    # Check if there are more pages
    while json_response['data']['node']['items']['pageInfo']['hasNextPage']:
        # Get the end cursor
        end_cursor = json_response['data']['node']['items']['pageInfo']['endCursor']

        # Update the query to fetch the next page
        query = """
        {
        node(id: \"""" + project_id + """\") { ... on ProjectV2 { items(first: 100, after: \"""" + end_cursor + """\") { pageInfo { endCursor hasNextPage } nodes{ id fieldValues(first: 8) { nodes{ ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon {  name }}} ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name }}}}} content{ ... on DraftIssue { title body } ...on Issue { title assignees(first: 10) { nodes{ login }}} ...on PullRequest { title assignees(first: 10) { nodes{ login }}}}}}}}}
        """

        # Make the request
        response = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)

        # Print the response
        json_response = response.json()
        for cur_item in json_response['data']['node']['items']['nodes']:
            new_item = handle_item(cur_item)
            if new_item != None:
                res.append(new_item)
            count = count + 1

    return res

def get_client():
    api_client = os.environ.get("api_client", None)
    api_secret = os.environ.get("api_secret", None)

    client = AskSageClient(api_client, api_secret, user_base_url='http://localhost:5002')
    return client

def get_answer(client, item):
    print("INFO: get_answer: analyzing item: " + item['title'])

    ret = client.query(message=item['body'], dataset='none', model='gpt4', system_prompt=system_prompt)
    if ret['status'] == 200:
        return convert_to_code(ret['message'])
    else:
        print("ERR: get_answer: ", ret['response'])
        return None

def append_chat(item, code):
    chat_obj = { "chats": [ { "user": "me", "message": item['body'] }, { "user": "gpt", "message": code } ] }
    client.append_chat(item['title'][:20], chat_obj)

def convert_to_code(code):
    # List of language identifiers
    languages = ['python', 'jsx', 'yaml', 'bash', 'shell', 'go', 'sql', 'code', 'Dockerfile', 'javascript', 'php', 'json', 'css', 'html']

    # Replace each language identifier
    for lang in languages:
        code = re.sub(r'```' + lang, '```', code, flags=re.DOTALL)

    # Replace text within triple backticks followed by a newline
    code = re.sub(r'```\n(.*?)```', r'<convert_code>\1</convert_code>', code, flags=re.DOTALL)
    # Replace text within triple backticks
    code = re.sub(r'```(.*?)```', r'<convert_code>\1</convert_code>', code, flags=re.DOTALL)

    return code

client = get_client()
items = get_github_project_items()
for item in items:
    code = get_answer(client, item)
    append_chat(item, code)
    print(code)