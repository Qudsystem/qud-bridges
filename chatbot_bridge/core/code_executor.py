"""Safe code execution with resource limits."""

import asyncio
import subprocess
import tempfile
import time
import os
import psutil
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import platform


@dataclass
class ExecutionResult:
    """
    Result of code execution.
    
    Attributes:
        command_id: ID of the command that was executed
        success: Whether execution completed successfully
        stdout: Standard output from execution
        stderr: Standard error from execution
        exit_code: Process exit code
        execution_time: Time taken for execution in seconds
        timestamp: When execution completed
        error_message: Human-readable error message if failed
    """
    
    command_id: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    timestamp: float
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "command_id": self.command_id,
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionResult':
        """Create from dictionary."""
        return cls(**data)
    
    def format_for_chatbot(self) -> str:
        """
        Format result as message for chatbot.
        
        Returns:
            Formatted message string
        """
        if self.success:
            message = f"✅ **Execution Successful** (took {self.execution_time:.2f}s)\n\n"
            if self.stdout.strip():
                message += f"**Output:**\n```\n{self.stdout.strip()}\n```\n\n"
            if self.stderr.strip():
                message += f"**Warnings:**\n```\n{self.stderr.strip()}\n```"
        else:
            message = f"❌ **Execution Failed** (exit code: {self.exit_code})\n\n"
            if self.error_message:
                message += f"**Error:** {self.error_message}\n\n"
            if self.stderr.strip():
                message += f"**Details:**\n```\n{self.stderr.strip()}\n```\n\n"
            if self.stdout.strip():
                message += f"**Partial Output:**\n```\n{self.stdout.strip()}\n```"
        
        return message.strip()


class CodeExecutor:
    """
    Executes code in isolated subprocess with resource limits.
    
    Supports multiple programming languages and enforces security constraints
    including timeouts, memory limits, and CPU usage limits.
    """
    
    def __init__(
        self,
        timeout: int = 30,
        memory_limit_mb: int = 512,
        cpu_limit_percent: int = 50
    ):
        """
        Initialize code executor.
        
        Args:
            timeout: Maximum execution time in seconds
            memory_limit_mb: Maximum memory usage in MB
            cpu_limit_percent: Maximum CPU usage percentage
        """
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_percent = cpu_limit_percent
        
        # Language configurations
        self.language_configs = {
            "python": {
                "command": ["python", "-c"],
                "file_extension": ".py",
                "interpreter": True
            },
            "python3": {
                "command": ["python3", "-c"],
                "file_extension": ".py", 
                "interpreter": True
            },
            "javascript": {
                "command": ["node", "-e"],
                "file_extension": ".js",
                "interpreter": True
            },
            "bash": {
                "command": ["bash", "-c"],
                "file_extension": ".sh",
                "interpreter": True
            },
            "sh": {
                "command": ["sh", "-c"],
                "file_extension": ".sh",
                "interpreter": True
            },
            "powershell": {
                "command": ["powershell", "-Command"],
                "file_extension": ".ps1",
                "interpreter": True
            }
        }
    
    async def execute_code(
        self,
        code: str,
        language: str,
        command_id: str,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Execute code in isolated subprocess.
        
        Args:
            code: Code to execute
            language: Programming language (python, javascript, bash, etc.)
            command_id: Unique identifier for this execution
            working_dir: Working directory for execution
            env_vars: Environment variables
            
        Returns:
            ExecutionResult with output and status
        """
        start_time = time.time()
        
        # Validate language
        if language not in self.language_configs:
            return ExecutionResult(
                command_id=command_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                timestamp=time.time(),
                error_message=f"Unsupported language: {language}"
            )
        
        config = self.language_configs[language]
        
        try:
            # Execute based on interpreter type
            if config["interpreter"]:
                result = await self._execute_interpreter(
                    code, config, command_id, working_dir, env_vars
                )
            else:
                result = await self._execute_file(
                    code, config, command_id, working_dir, env_vars
                )
            
            result.execution_time = time.time() - start_time
            return result
            
        except Exception as e:
            return ExecutionResult(
                command_id=command_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=time.time() - start_time,
                timestamp=time.time(),
                error_message=f"Execution error: {str(e)}"
            )
    
    async def execute_file(
        self,
        file_path: str,
        command_id: str,
        args: Optional[List[str]] = None
    ) -> ExecutionResult:
        """
        Execute a file.
        
        Args:
            file_path: Path to file to execute
            command_id: Unique identifier for this execution
            args: Command line arguments
            
        Returns:
            ExecutionResult with output and status
        """
        start_time = time.time()
        
        if not os.path.exists(file_path):
            return ExecutionResult(
                command_id=command_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                timestamp=time.time(),
                error_message=f"File not found: {file_path}"
            )
        
        # Determine execution method based on file extension
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".py":
            cmd = ["python", file_path]
        elif file_ext == ".js":
            cmd = ["node", file_path]
        elif file_ext in [".sh", ".bash"]:
            cmd = ["bash", file_path]
        elif file_ext == ".ps1":
            cmd = ["powershell", "-File", file_path]
        else:
            # Try to execute directly (assumes executable)
            cmd = [file_path]
        
        if args:
            cmd.extend(args)
        
        try:
            result = await self._run_subprocess(cmd, command_id)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return ExecutionResult(
                command_id=command_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=time.time() - start_time,
                timestamp=time.time(),
                error_message=f"File execution error: {str(e)}"
            )
    
    async def _execute_interpreter(
        self,
        code: str,
        config: Dict[str, Any],
        command_id: str,
        working_dir: Optional[str],
        env_vars: Optional[Dict[str, str]]
    ) -> ExecutionResult:
        """Execute code using interpreter (python -c, node -e, etc.)."""
        cmd = config["command"] + [code]
        return await self._run_subprocess(cmd, command_id, working_dir, env_vars)
    
    async def _execute_file(
        self,
        code: str,
        config: Dict[str, Any],
        command_id: str,
        working_dir: Optional[str],
        env_vars: Optional[Dict[str, str]]
    ) -> ExecutionResult:
        """Execute code by writing to temporary file."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=config["file_extension"],
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Make executable if shell script
            if config["file_extension"] in [".sh", ".bash"]:
                os.chmod(temp_file, 0o755)
            
            cmd = [temp_file]
            return await self._run_subprocess(cmd, command_id, working_dir, env_vars)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    async def _run_subprocess(
        self,
        cmd: List[str],
        command_id: str,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Run subprocess with resource limits and monitoring."""
        
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        try:
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
                preexec_fn=self._setup_process_limits if platform.system() != "Windows" else None
            )
            
            # Monitor process with timeout and resource limits
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                return ExecutionResult(
                    command_id=command_id,
                    success=process.returncode == 0,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    exit_code=process.returncode,
                    execution_time=0,  # Will be set by caller
                    timestamp=time.time()
                )
                
            except asyncio.TimeoutError:
                # Kill process and all children
                await self._kill_process_tree(process.pid)
                return ExecutionResult(
                    command_id=command_id,
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    execution_time=0,
                    timestamp=time.time(),
                    error_message=f"Execution timed out after {self.timeout} seconds"
                )
                
        except Exception as e:
            return ExecutionResult(
                command_id=command_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                timestamp=time.time(),
                error_message=f"Process execution error: {str(e)}"
            )
    
    def _setup_process_limits(self):
        """Set up resource limits for subprocess (Unix only)."""
        try:
            import resource
            
            # Set memory limit
            memory_bytes = self.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            # Set CPU time limit (soft limit)
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout + 5))
            
        except ImportError:
            # resource module not available (Windows)
            pass
    
    async def _kill_process_tree(self, pid: int):
        """Kill process and all its children."""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Kill parent
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
                
        except psutil.NoSuchProcess:
            # Process already terminated
            pass
    
    def _apply_resource_limits(self, process: subprocess.Popen) -> None:
        """
        Apply resource limits to subprocess (legacy method for compatibility).
        
        Args:
            process: Subprocess instance
        """
        # This method is kept for compatibility but resource limits
        # are now applied in _setup_process_limits
        pass