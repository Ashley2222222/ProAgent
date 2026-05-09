import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AI_API_KEY")
ENDPOINT_ID = "ep-20260511100953-rnlb2"  # 你的接入点ID

url = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
payload = {"model": ENDPOINT_ID, "input": [{"type": "text", "text": "测试文本"}]}

print("请求 URL:", url)
print("请求头:", headers)
print("请求体:", payload)

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print("状态码:", resp.status_code)
    print("响应内容:", resp.text)
    resp.raise_for_status()
    print("✅ API 调用成功")
except Exception as e:
    print(f"❌ 失败: {e}")
