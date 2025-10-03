import asyncio
import json
from typing import Dict, Any, List
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from .logging_config import logger

class WorkerManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tasks = {}
        self.workers_dir = Path("workers")
        self.workers_dir.mkdir(exist_ok=True)

        # Scalability improvements
        self.max_concurrent_tasks = config.get("workers", {}).get("max_concurrent_tasks", 10)
        self.cpu_workers = config.get("workers", {}).get("cpu_workers", 4)
        self.io_workers = config.get("workers", {}).get("io_workers", 20)

        # Process pool for CPU-intensive tasks
        self.process_pool = ProcessPoolExecutor(max_workers=self.cpu_workers)

        # Semaphore for limiting concurrent tasks
        self.task_semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        # Task priorities (higher number = higher priority)
        self.task_priorities = {
            "code_analysis": 1,
            "model_training": 3,
            "data_processing": 2,
            "file_processing": 1,
            "image_generation": 2,
            "text_to_image": 2
        }

    async def submit_task(self, task_type: str, data: Dict[str, Any], priority: int = None) -> str:
        """Submit a background task with priority-based queuing"""
        import secrets
        task_id = secrets.token_hex(16)

        if priority is None:
            priority = self.task_priorities.get(task_type, 1)

        task = {
            "id": task_id,
            "type": task_type,
            "data": data,
            "status": "pending",
            "priority": priority,
            "created_at": asyncio.get_event_loop().time()
        }

        self.tasks[task_id] = task

        # Start background processing with semaphore control
        asyncio.create_task(self._process_task_with_semaphore(task_id))

        logger.info(f"Submitted task {task_id} of type {task_type} with priority {priority}")
        return task_id

    async def _process_task_with_semaphore(self, task_id: str):
        """Process task with concurrency control"""
        async with self.task_semaphore:
            await self._process_task(task_id)

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task

    async def _process_task(self, task_id: str):
        """Process a background task"""
        task = self.tasks[task_id]
        try:
            task["status"] = "running"
            logger.info(f"Processing task {task_id}")

            # Route tasks based on type and resource requirements
            if task["type"] == "code_analysis":
                result = await self._analyze_code(task["data"])
            elif task["type"] == "model_training":
                result = await self._run_cpu_task(self._train_model_sync, task["data"])
            elif task["type"] == "data_processing":
                result = await self._process_data(task["data"])
            elif task["type"] == "image_generation":
                result = await self._generate_image(task["data"])
            elif task["type"] == "text_to_image":
                result = await self._text_to_image(task["data"])
            else:
                result = {"error": f"Unknown task type: {task['type']}"}

            task["status"] = "completed"
            task["result"] = result
            task["completed_at"] = asyncio.get_event_loop().time()

            logger.info(f"Completed task {task_id}")

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            logger.error(f"Task {task_id} failed: {e}")

    async def _analyze_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code (placeholder)"""
        await asyncio.sleep(2)  # Simulate processing time
        code = data.get("code", "")
        return {
            "lines": len(code.split("\n")),
            "characters": len(code),
            "analysis": "Basic code analysis completed"
        }

    async def _train_model(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Train model (placeholder)"""
        await asyncio.sleep(10)  # Simulate long training
        return {
            "accuracy": 0.95,
            "epochs": data.get("epochs", 10),
            "status": "Model training completed"
        }

    async def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data (placeholder)"""
        await asyncio.sleep(1)
        return {
            "processed_items": len(data.get("items", [])),
            "status": "Data processing completed"
        }

    async def _generate_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using diffusion model"""
        # Simulate image generation time (30-120 seconds)
        await asyncio.sleep(5)  # Placeholder - would be much longer for real generation

        prompt = data.get("prompt", "")
        model = data.get("model", "stable-diffusion")
        width = data.get("width", 512)
        height = data.get("height", 512)

        # Placeholder result - in real implementation, this would save actual image
        return {
            "image_url": f"/generated_images/{data.get('user_id', 'anonymous')}/generated_{asyncio.get_event_loop().time()}.png",
            "prompt": prompt,
            "model": model,
            "dimensions": f"{width}x{height}",
            "status": "Image generated successfully"
        }

    async def _text_to_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert text to image"""
        # Similar to image generation but for text-to-image conversion
        await asyncio.sleep(3)

        text = data.get("text", "")
        model = data.get("model", "stable-diffusion")

        return {
            "image_url": f"/converted_images/{data.get('user_id', 'anonymous')}/text_to_image_{asyncio.get_event_loop().time()}.png",
            "original_text": text[:100] + "..." if len(text) > 100 else text,
            "model": model,
            "status": "Text converted to image successfully"
        }

    async def _run_cpu_task(self, func, *args, **kwargs):
        """Run CPU-intensive task in process pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.process_pool, func, *args, **kwargs)

    def _train_model_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous version of model training for process pool"""
        import time
        time.sleep(10)  # Simulate long training
        return {
            "accuracy": 0.95,
            "epochs": data.get("epochs", 10),
            "status": "Model training completed"
        }

    def list_workers(self) -> List[Dict[str, Any]]:
        """List available worker scripts"""
        workers = []
        for file in self.workers_dir.glob("*.py"):
            workers.append({
                "name": file.stem,
                "path": str(file),
                "type": "python"
            })
        return workers

    async def run_worker(self, worker_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run a worker script"""
        worker_path = self.workers_dir / f"{worker_name}.py"
        if not worker_path.exists():
            raise ValueError(f"Worker {worker_name} not found")

        # For now, just simulate running
        logger.info(f"Running worker {worker_name} with args: {args}")
        return {
            "worker": worker_name,
            "status": "completed",
            "output": f"Worker {worker_name} executed successfully"
        }

    def shutdown(self):
        """Shutdown worker manager and cleanup resources"""
        self.process_pool.shutdown(wait=True)
        logger.info("Worker manager shutdown completed")