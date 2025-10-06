import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import logging
from typing import Dict, Any, Optional
import json
from config import TMDB_BASE_URL, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TMDB API 代理中转站",
    description="TMDB API 代理中转站",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TMDBProxy:
    
    def __init__(self):
        self.base_url = TMDB_BASE_URL
        self.timeout = REQUEST_TIMEOUT
        
    async def forward_request(self, request: Request, path: str) -> Dict[str, Any]:
        
        target_url = f"{self.base_url}/{path.lstrip('/')}"
        
        query_params = dict(request.query_params)
        
        headers = dict(request.headers)
        headers.pop('host', None)
        headers.pop('content-length', None)
        
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
            except Exception as e:
                logger.warning(f"无法读取请求体: {e}")
        
        logger.info(f"转发请求: {request.method} {target_url}")
        logger.info(f"查询参数: {query_params}")
        
        try:
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(
                timeout=self.timeout,
                limits=limits,
                verify=True,
                follow_redirects=True,
                proxies=None
            ) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    params=query_params,
                    headers=headers,
                    content=body
                )
                
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"TMDB API 错误: {e.response.text}"
            )
        except httpx.ConnectError as e:
            logger.error(f"连接错误: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"无法连接到 TMDB API: {str(e)}"
            )
        except httpx.TimeoutException as e:
            logger.error(f"请求超时: {e}")
            raise HTTPException(
                status_code=504,
                detail=f"请求超时: {str(e)}"
            )
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"代理请求失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"代理服务错误: {str(e)}"
            )

proxy = TMDBProxy()

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "TMDB API 代理中转站正在运行",
        "version": "1.0.0",
        "docs": "/docs",
        "original_api": TMDB_BASE_URL,
        "usage": "直接使用 TMDB API 的路径，例如: /movie/popular, /search/movie?query=avengers"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "proxy": "running"}

@app.get("/{path:path}")
async def proxy_get(request: Request, path: str):
    return await proxy.forward_request(request, path)

@app.post("/{path:path}")
async def proxy_post(request: Request, path: str):
    return await proxy.forward_request(request, path)

@app.put("/{path:path}")
async def proxy_put(request: Request, path: str):
    return await proxy.forward_request(request, path)

@app.patch("/{path:path}")
async def proxy_patch(request: Request, path: str):
    return await proxy.forward_request(request, path)

@app.delete("/{path:path}")
async def proxy_delete(request: Request, path: str):
    return await proxy.forward_request(request, path)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"收到请求: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"响应状态: {response.status_code}")
    return response

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="TMDB API 代理中转站")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=6371, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    
    args = parser.parse_args()
    
    print("🚀 启动 TMDB API 代理中转站...")
    print(f"📡 代理目标: {TMDB_BASE_URL}")
    print(f"🌐 服务地址: http://{args.host}:{args.port}")
    print(f"📖 API 文档: http://{args.host}:{args.port}/docs")
    print("=" * 60)
    print("💡 使用示例:")
    print(f"  GET http://{args.host}:{args.port}/movie/popular")
    print(f"  GET http://{args.host}:{args.port}/search/movie?query=avengers")
    print(f"  GET http://{args.host}:{args.port}/tv/popular")
    print(f"  GET http://{args.host}:{args.port}/trending/all/day")
    print("=" * 60)
    
    uvicorn.run(
        "proxy_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main() 