import requests
import json

class DifyAPI:
    def __init__(self, api_key, api_base_url="http://103.194.107.232/v1"):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, message, conversation_id=None, user=None):
        """使用 Chat API 进行对话"""
        endpoint = f"{self.api_base_url}/chat-messages"
        
        payload = {
            "inputs": {},
            "query": message,
            "response_mode": "blocking",
            "conversation_id": conversation_id
        }
        
        if user:
            payload["user"] = 'dify_wuyu'

        

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            #打印http返回的状态码
            print(f"HTTP 状态码: {response.status_code}")

            #打印http返回的响应消息体
            print(f"HTTP 响应消息体: {response.text}")

            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return None

    def text_completion(self, prompt):
        """使用 Completion API 生成文本"""
        endpoint = f"{self.api_base_url}/completion-messages"
        
        payload = {
            "inputs": {},
            "query": prompt,
            "response_mode": "streaming",
            "user": "dify_wuyu"
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return None

def main():
    # 替换为你的 API 密钥
    api_key = "app-wsXdNA9L8e7jahW1a9W4RPO6"
    dify = DifyAPI(api_key)

    # 测试 Chat API
    print("测试 Chat API:")
    chat_response = dify.chat_completion("你好，请介绍一下你自己", user="dify_wuyu")
    if chat_response:
        print(f"Chat 回复: {json.dumps(chat_response, ensure_ascii=False, indent=2)}")

    # 测试 Completion API
    print("\n测试 Completion API:")
    completion_response = dify.text_completion("写一个简短的故事")
    if completion_response:
        print(f"Completion 回复: {json.dumps(completion_response, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main() 