import os
import sys
import json
import base64
import requests


if __name__ == "__main__":

    GITHUB_REPO = os.getenv('GITHUB_REPOSITORY')
    GITHUB_BRANCH = "master"
    GITHUB_FILE = "test.yml"
    HEADERS = {
        'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.5) Gecko/20120601 Firefox/10.0.5',
        'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']
    }

    # Get current master data
    head_response = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}')
    head_data = json.loads(head_response.text)

    HEAD = {
        'sha' : head_data['object']['sha'],
        'url' : head_data['object']['url'],
    }

    # Get current head commit
    commit_response = requests.get(HEAD['url'])
    commit_data = json.loads(commit_response.text)

    # Remove unessesary files
    for key in list(commit_data.keys()):
        if key not in ['sha', 'tree']:
            del commit_data[key]
    HEAD['commit'] = commit_data

    # Get the tree of the commit
    tree_response = requests.get(HEAD['commit']['tree']['url'])
    tree_data = json.loads(tree_response.text)
    HEAD['tree'] = { 'sha' : tree_data['sha'] }

    # Get the latest commit, and target file data
    for obj in tree_data['tree']:
        if obj['path'] == GITHUB_FILE:
            file_response = requests.get(obj['url'])
            file_data = json.loads(file_response.text)
            data = base64.b64decode(file_data['content'])
            break

    # Content of the file to replace
    new_file = 'This action has been ran {os.getenv("GITHUB_RUN_NUMBER")} times'

    # Send new file to github
    file_change_response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/blobs",
        data=json.dumps({
            'content' : new_file,
            'encoding' : 'utf-8'
        }),
        headers=HEADERS
    )
    file_change_data = json.loads(file_change_response.text)

    if 'sha' not in file_change_data:
        print(file_change_data)
        sys.exit(1)

    HEAD['UPDATE'] = { 'sha' : file_change_data['sha'] }

    # Create new tree with file
    tree_create_response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/trees",
        data=json.dumps({
            "base_tree": HEAD['tree']['sha'],
            "tree": [{
                "path": GITHUB_FILE,
                "mode": "100644",
                "type": "blob",
                "sha": HEAD['UPDATE']['sha']
            }]
        }),
        headers=HEADERS
    )
    tree_create_data = json.loads(tree_create_response.text)

    if 'sha' not in tree_create_data:
        print(tree_create_data)
        sys.exit(1)

    HEAD['UPDATE']['tree'] = { 'sha' : tree_create_data['sha'] }

    # Create new commit
    commit_create_response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/commits",
        data=json.dumps({
            "message": "Automatic file change",
            "parents": [HEAD['commit']['sha']],
            "tree": HEAD['UPDATE']['tree']['sha']
        }),
        headers=HEADERS
    )
    commit_create_data = json.loads(commit_create_response.text)

    if 'sha' not in commit_create_data:
        print(commit_create_data)
        sys.exit(1)

    HEAD['UPDATE']['commit'] = { 'sha' : commit_create_data['sha'] }

    # Update head
    head_update_response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}",
        data=json.dumps({
            "sha": HEAD['UPDATE']['commit']['sha']
        }),
        headers=HEADERS
    )
    head_update_data = json.loads(head_update_response.text)

    if 'object' in head_update_data:
        sys.exit(0)
    else:
        print(head_update_data['message'])
        sys.exit(1)
