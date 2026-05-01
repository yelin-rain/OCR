import httpx
import asyncio
from typing import Dict, Any
from app.core.config import settings

class BaiduOCRProvider:
    """
    Provider for Baidu AI Studio PaddleOCR-VL API (V2 Jobs).
    """
    async def ocr_general_basic(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        通过 AI Studio V2 Jobs 接口进行图片文字识别
        1. POST /jobs (multipart/form-data) 获取 jobId
        2. 轮询 GET /jobs/{jobId} 获取结果
        """
        if not settings.OCR_ACCESS_TOKEN:
            raise Exception("OCR_ACCESS_TOKEN is not configured in .env")

        headers = {
            "Authorization": f"token {settings.OCR_ACCESS_TOKEN}"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # 1. 提交任务 (Multipart)
                print(f"Submitting OCR job to: {settings.OCR_API_URL}")
                files = {
                    "file": ("image.png", image_bytes, "image/png")
                }
                data = {
                    "fileType": 1, 
                    "model": settings.OCR_MODEL or "PaddleOCR-VL-1.5"
                }
                
                resp = await client.post(
                    settings.OCR_API_URL, 
                    files=files, 
                    data=data,
                    headers=headers
                )
                
                if resp.status_code != 200:
                    raise Exception(f"Job submission failed: {resp.status_code} - {resp.text}")
                
                job_resp = resp.json()
                if job_resp.get("code") != 0:
                    raise Exception(f"AI Studio Error (Post): {job_resp.get('msg')} (Code: {job_resp.get('code')})")
                
                job_id = job_resp.get("data", {}).get("jobId")
                if not job_id:
                    raise Exception(f"Failed to get jobId from response: {job_resp}")
                
                print(f"OCR Job submitted successfully. Job ID: {job_id}")

                # 2. 轮询结果
                status_url = f"{settings.OCR_API_URL}/{job_id}"
                max_retries = 90 # 最多等 3分钟 (90 * 2s)
                for i in range(max_retries):
                    await asyncio.sleep(2) # 每2秒查一次
                    
                    status_resp = await client.get(status_url, headers=headers)
                    if status_resp.status_code != 200:
                        continue
                    
                    status_data = status_resp.json()
                    if status_data.get("code") != 0:
                        raise Exception(f"AI Studio Error (Get): {status_data.get('msg')}")
                    
                    job_info = status_data.get("data", {})
                    state = job_info.get("state")
                    
                    # AI Studio 成功状态为 'done'
                    if state == "done":
                        print(f"OCR Job {job_id} done. Fetching results...")
                        result_url_info = job_info.get("resultUrl", {})
                        json_url = result_url_info.get("jsonUrl")
                        
                        if not json_url:
                            raise Exception("Job done but no jsonUrl found in response.")

                        # 获取最终的 JSON 结果
                        res = await client.get(json_url)
                        if res.status_code != 200:
                            raise Exception(f"Failed to fetch results from {json_url}")
                        
                        final_result = res.json()
                        
                        # 3. 解析并重组 JSON 数据
                        # 用户需求：提取 block_content 并拼接
                        try:
                            parsing_res_list = final_result.get("result", {}).get("layoutParsingResults", [])[0].get("prunedResult", {}).get("parsing_res_list", [])
                            
                            extracted_texts = []
                            for block in parsing_res_list:
                                content = block.get("block_content")
                                if content:
                                    extracted_texts.append(content)
                            
                            # 使用换行符拼接所有文本块
                            full_text = "\n".join(extracted_texts)
                            
                            # 如果提取到了内容，覆盖原本的 markdown.text以供前端显示
                            if full_text:
                                if "result" not in final_result:
                                    final_result["result"] = {}
                                if "layoutParsingResults" not in final_result["result"]:
                                    final_result["result"]["layoutParsingResults"] = [{}]
                                if "markdown" not in final_result["result"]["layoutParsingResults"][0]:
                                    final_result["result"]["layoutParsingResults"][0]["markdown"] = {}
                                
                                final_result["result"]["layoutParsingResults"][0]["markdown"]["text"] = full_text
                                print(f"Successfully extracted and concatenated {len(extracted_texts)} blocks.")
                                
                        except Exception as e:
                            print(f"Error parsing block_content: {e}. Falling back to default response.")

                        # 转换格式以适配前端渲染逻辑 (result.layoutParsingResults[0].markdown.text)
                        # 注意：原始返回可能是多行 JSONL 或单个 JSON，这里我们做一个简单的适配
                        # 如果 final_result 已经是完整结构（如上面的 sample），直接返回即可；
                        # 但为了稳妥，遵循我们约定的结构：
                        # 前端期望: data.result.layoutParsingResults[0].markdown.text
                        
                        # 检查 final_result 的结构是否已经符合前端预期
                        if final_result.get("result", {}).get("layoutParsingResults"):
                             return final_result
                        
                        # 如果不符合（比如是纯字典），则包装一下
                        return {
                            "result": {
                                "layoutParsingResults": [final_result]
                            }
                        }

                    elif state == "failed":
                        error_msg = job_info.get("errorMsg", "Unknown AI Studio Error")
                        raise Exception(f"OCR Pipeline failed: {error_msg}")
                    else:
                        if i % 5 == 0:
                            print(f"Job {job_id} current state: {state}...")
                
                raise Exception(f"OCR Job {job_id} timed out after {max_retries} seconds.")
                
            except Exception as e:
                print(f"Exception during AI Studio OCR Workflow: {e}")
                raise e

# 单例
baidu_provider = BaiduOCRProvider()
