import json
import os
import base64
import requests

import discord
from discord import app_commands

# Used for basic Discord Interactions
from discord_interactions import verify_key, InteractionType, InteractionResponseType

from openai import OpenAI

job_listing_websites = [
    "indeed.com",
    "glassdoor.com",
    "linkedin.com",
    "monster.com",
    "ziprecruiter.com",
    "coporatetools.com",
    "https://info.encs.vancouver.wsu.edu/student-success/career-resources/",
    "https://www.nlight.net/careers/"
]

def lambda_handler(event, context):
    # REPLACE with your Public Key from the Discord Developer Portal
    PUBLIC_KEY = os.environ['DISCORD_PUBLIC_KEY']
    
    # Get headers and body
    headers = event.get('headers', {})
    signature = headers.get('x-signature-ed25519')
    timestamp = headers.get('x-signature-timestamp')

    if event.get("isBase64Encoded"):
        # Decode the string to bytes
        body = base64.b64decode(event["body"]).decode(
            'utf-8')
    else:
        # Assume it's a regular string, convert to bytes if needed
        body = event.get('body', '')
    #body = event.get('body', '')

    # Debugging information to print to the logs
    print(f"Signature: {type(signature)} {signature}, Timestamp: {type(timestamp)} {timestamp}")
    print(f"Data from BODY: {type(body)} {body}")

    if isinstance(body, str):
        data = json.loads(body)
    else:
        data = body

    # 1. Mandatory Security Verification
    # Discord requires you to verify that the request came from them

    # Skip security verification if "isTest" is set
    if data.get("isTest", None) == None:

        # Security Check: Verify the request origin
        if not signature or not timestamp or not verify_key(data.encode('utf-8'), signature, timestamp, PUBLIC_KEY):
            return {
                'statusCode': 401,
                'body': json.dumps('Invalid request signature')
            }
            
    # Parse the verified payload
    interaction = json.loads(data)
    interaction_type = interaction.get('type')
    result = None

    # 3. Handle PING (Initial Discord Verification)
    if data.get("type") == 1:
        result = {
            "statusCode": 200,
            'headers': {'Content-Type': 'application/json'},
            "body": json.dumps({"type": 1})
        }

    # 4. Handle Slash Commands (Interaction Type 2)
    if data.get("type") == 2:
        global_name = data.get("member").get("user").get("global_name")
        slash_name = data.get("data").get("name").lower()
        options = data.get("data").get("options")

        resolved = data.get("data").get("resolved")
        if resolved:
            attachments = resolved.get("attachments")
        else:
            attachments = []
        
        # Handle different slash commands by name
        if slash_name == "ping":
            if isinstance(options, list):
                # This is an unfair way of assuming the first entry is always a message
                message = options[0].get("value")
            else:
                message = ""

            content = f"Hello, {global_name}, from AWS Lambda! Message: {message}"
        elif slash_name == "dadjoke":
            content = requests.get('https://icanhazdadjoke.com', headers={"Accept":"application/json"}).json()['joke']
        elif slash_name == "aichat":
            prompt = options[0].get("value")
            print(prompt)

            #needed for our discord interaction
            interaction_id = data.get("id")
            interaction_token = data.get("token")
            app_id = os.environ['APP_ID']

            #stole this from discord documentation->interactions->receiving and responding 
            #used to handle responses to discord to my understanding
            url = f"https://discord.com/api/v10/interactions/{interaction_id}/{interaction_token}/callback"            
            # manually tell discord we got this
            requests.post(
                url,
                json={"type": 5}
            )

            #now continue our ai request
            client = OpenAI(
                # This is the default and can be omitted
                api_key=os.environ.get("OPENAI_API_KEY"),
            )            
            
            response = client.responses.create(
                model="gpt-5.5",
                instructions="You are a Oswald, a helpful and funny penguin mascot for Clark College in Vancouver, Washington and especially helpful with coding assistance. Occasionally you interject a fun fact about Clark College in Vancouver, WA or just penguins in general. Include the question you were asked before providing the answer. Keep your answer short with no more than 1950 characters but helpful. Restrict web searches to engrcs.com and clark.edu",
                input=prompt,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [os.environ.get("VECTOR_STORE_ID")]  # Attach your vector store here
                    },
                    {
                        "type": "web_search"
                    }
                ]
            )

            print(response.output_text)
            content = response.output_text

            #create another url for editing the message
            edit_msg_url=f"https://discord.com/api/v10/webhooks/{app_id}/{interaction_token}/messages/@original"
            
            #we are going to 'edit' the respond we sent earlier now with the response from OpenAI
            print(f"Sending a PATCH to update {edit_msg_url}")
            patch_results = requests.patch(
                edit_msg_url,
                json={"content": content[:2000]}
            )
            print(f"Patch results: {patch_results.text}")

            #we must return early since this is a different type of payload (had to ask claud about this one)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"type": 5})
            }   
        elif slash_name == "findmeajob":
            document_url_id = options[0].get("value")
            if len(options) > 1:
                prompt = options[1].get("value")
            else:
                prompt = "Find me a job!"
                
            document_url = attachments[document_url_id].get("url")
            print(f"Document URL: {document_url}, Prompt: {prompt}")

            #needed for our discord interaction
            interaction_id = data.get("id")
            interaction_token = data.get("token")
            app_id = os.environ['APP_ID']

            #stole this from discord documentation->interactions->receiving and responding 
            #used to handle responses to discord to my understanding
            url = f"https://discord.com/api/v10/interactions/{interaction_id}/{interaction_token}/callback"            
            # manually tell discord we got this
            requests.post(
                url,
                json={"type": 5}
            )

            #now continue our ai request
            client = OpenAI(
                # This is the default and can be omitted
                api_key=os.environ.get("OPENAI_API_KEY"),
            )            
            
            response = client.responses.create(
                model="gpt-5.5",
                instructions=f"You are a helpful job search assistant. Using the linked resume at {document_url} and narrowing the search based on the provided prompt use the provided URLs to find the best 5 matches and offer any advice on improving resume to meet these matches in under 1950 characters including links to what you found: {', '.join(job_listing_websites)}",
                input=prompt,
                tools=[
                    {
                        "type": "web_search"
                    }
                ]
            )

            print(response.output_text)
            content = response.output_text

            #create another url for editing the message
            edit_msg_url=f"https://discord.com/api/v10/webhooks/{app_id}/{interaction_token}/messages/@original"
            
            #we are going to 'edit' the respond we sent earlier now with the response from OpenAI
            print(f"Sending a PATCH to update {edit_msg_url}")
            patch_results = requests.patch(
                edit_msg_url,
                json={"content": content[:2000]}
            )
            print(f"Patch results: {patch_results.text}")

            #we must return early since this is a different type of payload (had to ask claud about this one)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"type": 5})
            }  
        elif slash_name =="oswaldsay":
            if isinstance(options, list):
                message = options[0].get("value")
            else:
                message=f"Hello, {global_name}!"
            
            art = r""" 
            \
             \
                .--.
               |o_o |
               |:_/ |
              //   \ \
             (|  C  | )
            /'\_   _/`\
            \___)=(___/
             """ 

            bubble_width=len(message)+2 # padding
            # formatting speech bubble, adding oswald
            result=""
            result+=(" " + "_"*bubble_width)+"\n"
            result+="< " + message+" >\n"
            result+=(" " + "-"*bubble_width)
            result+=art
            content = "```" + result + "```" #discord code block formatting
            
        else: 
            content = "No response found for slash command."

        result = {
            "statusCode": 200,
            'headers': {'Content-Type': 'application/json'},
            "body": json.dumps({
                "type": 4,  # Response type: ChannelMessageWithSource
                "data": {"content": content}
            })
        }

    if result != None:
        print(f"Result: {result}")
        return result
    else:
        print("No result")
        return {"statusCode": 404}
