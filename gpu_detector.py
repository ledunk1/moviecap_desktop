import subprocess
import platform
import re
import os
from typing import Dict, List, Tuple, Optional

class GPUDetector:
    def __init__(self):
        self.system = platform.system()
        self.gpu_info = {}
        self.hardware_encoders = []
        self.hardware_decoders = []
        self.opencl_support = False
        self.opencv_opencl = False
        
    def detect_all(self) -> Dict:
        """Detect all GPU and hardware acceleration capabilities"""
        self.detect_gpus()
        self.detect_ffmpeg_hardware_support()
        self.detect_opencl_support()
        self.detect_opencv_opencl()
        
        return {
            'gpus': self.gpu_info,
            'hardware_encoders': self.hardware_encoders,
            'hardware_decoders': self.hardware_decoders,
            'opencl_support': self.opencl_support,
            'opencv_opencl': self.opencv_opencl,
            'recommended_settings': self.get_recommended_settings()
        }
    
    def detect_gpus(self):
        """Detect available GPUs"""
        if self.system == "Windows":
            self._detect_gpus_windows()
        elif self.system == "Linux":
            self._detect_gpus_linux()
        elif self.system == "Darwin":  # macOS
            self._detect_gpus_macos()
    
    def _detect_gpus_windows(self):
        """Detect GPUs on Windows using wmic and dxdiag"""
        try:
            # Use wmic to get GPU information
            result = subprocess.run([
                'wmic', 'path', 'win32_VideoController', 'get', 
                'name,adapterram,driverversion', '/format:csv'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 4:
                            name = parts[2].strip()
                            if name and name != "Name":
                                self._classify_gpu(name, parts[1].strip(), parts[3].strip())
        except Exception as e:
            print(f"Error detecting Windows GPUs: {e}")
            
        # Fallback: Try to detect through DirectX
        try:
            result = subprocess.run(['dxdiag', '/t', 'temp_dxdiag.txt'], 
                                  capture_output=True, timeout=15)
            if os.path.exists('temp_dxdiag.txt'):
                with open('temp_dxdiag.txt', 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    self._parse_dxdiag_output(content)
                os.remove('temp_dxdiag.txt')
        except Exception as e:
            print(f"Error with dxdiag: {e}")
    
    def _detect_gpus_linux(self):
        """Detect GPUs on Linux using lspci and other tools"""
        try:
            # Use lspci to detect GPUs
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'VGA compatible controller' in line or 'Display controller' in line:
                        self._classify_gpu_linux(line)
        except Exception as e:
            print(f"Error detecting Linux GPUs with lspci: {e}")
        
        # Try nvidia-smi for NVIDIA GPUs
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 3:
                            self.gpu_info['nvidia'] = {
                                'name': parts[0],
                                'memory': f"{parts[1]} MB",
                                'driver': parts[2],
                                'type': 'NVIDIA'
                            }
        except Exception:
            pass
        
        # Try intel_gpu_top for Intel GPUs
        try:
            result = subprocess.run(['intel_gpu_top', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'Intel' in result.stdout:
                self.gpu_info['intel'] = {
                    'name': 'Intel Integrated Graphics',
                    'type': 'Intel',
                    'driver': 'Available'
                }
        except Exception:
            pass
    
    def _detect_gpus_macos(self):
        """Detect GPUs on macOS using system_profiler"""
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                  capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                self._parse_macos_gpu_output(result.stdout)
        except Exception as e:
            print(f"Error detecting macOS GPUs: {e}")
    
    def _classify_gpu(self, name: str, memory: str = "", driver: str = ""):
        """Classify GPU by vendor"""
        name_lower = name.lower()
        
        if 'nvidia' in name_lower or 'geforce' in name_lower or 'quadro' in name_lower or 'tesla' in name_lower:
            self.gpu_info['nvidia'] = {
                'name': name,
                'memory': memory,
                'driver': driver,
                'type': 'NVIDIA'
            }
        elif 'amd' in name_lower or 'radeon' in name_lower or 'rx ' in name_lower:
            self.gpu_info['amd'] = {
                'name': name,
                'memory': memory,
                'driver': driver,
                'type': 'AMD'
            }
        elif 'intel' in name_lower or 'hd graphics' in name_lower or 'iris' in name_lower or 'uhd graphics' in name_lower:
            self.gpu_info['intel'] = {
                'name': name,
                'memory': memory,
                'driver': driver,
                'type': 'Intel'
            }
    
    def _classify_gpu_linux(self, line: str):
        """Classify GPU from Linux lspci output"""
        line_lower = line.lower()
        
        if 'nvidia' in line_lower:
            match = re.search(r'NVIDIA.*?(\[.*?\])', line)
            name = match.group(0) if match else "NVIDIA GPU"
            self.gpu_info['nvidia'] = {
                'name': name,
                'type': 'NVIDIA',
                'driver': 'Available'
            }
        elif 'amd' in line_lower or 'radeon' in line_lower:
            match = re.search(r'AMD.*?(\[.*?\])', line)
            name = match.group(0) if match else "AMD GPU"
            self.gpu_info['amd'] = {
                'name': name,
                'type': 'AMD',
                'driver': 'Available'
            }
        elif 'intel' in line_lower:
            match = re.search(r'Intel.*?(\[.*?\])', line)
            name = match.group(0) if match else "Intel GPU"
            self.gpu_info['intel'] = {
                'name': name,
                'type': 'Intel',
                'driver': 'Available'
            }
    
    def _parse_dxdiag_output(self, content: str):
        """Parse DirectX diagnostic output"""
        lines = content.split('\n')
        current_display = None
        
        for line in lines:
            line = line.strip()
            if 'Card name:' in line:
                name = line.split('Card name:')[1].strip()
                self._classify_gpu(name)
            elif 'Display Memory:' in line:
                memory = line.split('Display Memory:')[1].strip()
                # Update the last added GPU with memory info
                for gpu_key in self.gpu_info:
                    if 'memory' not in self.gpu_info[gpu_key] or not self.gpu_info[gpu_key]['memory']:
                        self.gpu_info[gpu_key]['memory'] = memory
                        break
    
    def _parse_macos_gpu_output(self, output: str):
        """Parse macOS system_profiler output"""
        lines = output.split('\n')
        current_gpu = {}
        
        for line in lines:
            line = line.strip()
            if 'Chipset Model:' in line:
                name = line.split('Chipset Model:')[1].strip()
                self._classify_gpu(name)
            elif 'VRAM (Total):' in line:
                memory = line.split('VRAM (Total):')[1].strip()
                # Update the last added GPU with memory info
                for gpu_key in self.gpu_info:
                    if 'memory' not in self.gpu_info[gpu_key] or not self.gpu_info[gpu_key]['memory']:
                        self.gpu_info[gpu_key]['memory'] = memory
                        break
    
    def detect_ffmpeg_hardware_support(self):
        """Detect FFmpeg hardware encoder/decoder support"""
        try:
            # Check for encoders
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self._parse_ffmpeg_encoders(result.stdout)
        except Exception as e:
            print(f"Error detecting FFmpeg encoders: {e}")
        
        try:
            # Check for decoders
            result = subprocess.run(['ffmpeg', '-decoders'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self._parse_ffmpeg_decoders(result.stdout)
        except Exception as e:
            print(f"Error detecting FFmpeg decoders: {e}")
    
    def _parse_ffmpeg_encoders(self, output: str):
        """Parse FFmpeg encoders output"""
        hardware_encoders = [
            'h264_nvenc', 'hevc_nvenc', 'av1_nvenc',  # NVIDIA
            'h264_amf', 'hevc_amf', 'av1_amf',        # AMD
            'h264_qsv', 'hevc_qsv', 'av1_qsv',        # Intel Quick Sync
            'h264_videotoolbox', 'hevc_videotoolbox', 'prores_videotoolbox'  # macOS
        ]
        
        for encoder in hardware_encoders:
            if encoder in output:
                self.hardware_encoders.append(encoder)
    
    def _parse_ffmpeg_decoders(self, output: str):
        """Parse FFmpeg decoders output"""
        hardware_decoders = [
            'h264_cuvid', 'hevc_cuvid', 'av1_cuvid',  # NVIDIA
            'h264_qsv', 'hevc_qsv', 'av1_qsv',        # Intel Quick Sync
            'h264_videotoolbox', 'hevc_videotoolbox'   # macOS
        ]
        
        for decoder in hardware_decoders:
            if decoder in output:
                self.hardware_decoders.append(decoder)
    
    def detect_opencl_support(self):
        """Detect OpenCL support"""
        try:
            # Try to import OpenCL
            import pyopencl as cl
            platforms = cl.get_platforms()
            if platforms:
                self.opencl_support = True
                return True
        except ImportError:
            pass
        except Exception:
            pass
        
        # Alternative: Check for OpenCL through system commands
        try:
            if self.system == "Windows":
                # Check for OpenCL.dll
                opencl_paths = [
                    r"C:\Windows\System32\OpenCL.dll",
                    r"C:\Windows\SysWOW64\OpenCL.dll"
                ]
                for path in opencl_paths:
                    if os.path.exists(path):
                        self.opencl_support = True
                        return True
            elif self.system == "Linux":
                # Check for OpenCL libraries
                result = subprocess.run(['ldconfig', '-p'], capture_output=True, text=True)
                if 'libOpenCL' in result.stdout:
                    self.opencl_support = True
                    return True
        except Exception:
            pass
        
        return False
    
    def detect_opencv_opencl(self):
        """Detect OpenCV OpenCL support"""
        try:
            import cv2
            if cv2.ocl.haveOpenCL():
                self.opencv_opencl = True
                return True
        except ImportError:
            pass
        except Exception:
            pass
        
        return False
    
    def get_recommended_settings(self) -> Dict:
        """Get recommended encoding settings based on detected hardware"""
        settings = {
            'encoder': 'libx264',  # Default software encoder
            'decoder': 'auto',
            'preset': 'medium',
            'threads': 4,
            'hardware_acceleration': False
        }
        
        # Prioritize hardware encoders
        if 'nvidia' in self.gpu_info:
            if 'h264_nvenc' in self.hardware_encoders:
                settings['encoder'] = 'h264_nvenc'
                settings['preset'] = 'p4'  # NVENC preset
                settings['hardware_acceleration'] = True
            if 'h264_cuvid' in self.hardware_decoders:
                settings['decoder'] = 'h264_cuvid'
        
        elif 'intel' in self.gpu_info:
            if 'h264_qsv' in self.hardware_encoders:
                settings['encoder'] = 'h264_qsv'
                settings['preset'] = 'medium'
                settings['hardware_acceleration'] = True
            if 'h264_qsv' in self.hardware_decoders:
                settings['decoder'] = 'h264_qsv'
        
        elif 'amd' in self.gpu_info:
            if 'h264_amf' in self.hardware_encoders:
                settings['encoder'] = 'h264_amf'
                settings['preset'] = 'balanced'
                settings['hardware_acceleration'] = True
        
        # macOS VideoToolbox
        if self.system == "Darwin":
            if 'h264_videotoolbox' in self.hardware_encoders:
                settings['encoder'] = 'h264_videotoolbox'
                settings['hardware_acceleration'] = True
        
        return settings
    
    def get_status_messages(self) -> List[str]:
        """Get formatted status messages for display"""
        messages = []
        
        # GPU Detection Messages
        if 'nvidia' in self.gpu_info:
            messages.append("🟢 NVIDIA GPU detected")
            messages.append(f"   └─ {self.gpu_info['nvidia']['name']}")
        
        if 'amd' in self.gpu_info:
            messages.append("🔴 AMD GPU detected")
            messages.append(f"   └─ {self.gpu_info['amd']['name']}")
        
        if 'intel' in self.gpu_info:
            messages.append("🔷 Intel GPU detected")
            messages.append(f"   └─ {self.gpu_info['intel']['name']}")
        
        if not self.gpu_info:
            messages.append("⚠️  No dedicated GPU detected")
        
        # Hardware Acceleration Status
        if self.hardware_encoders or self.hardware_decoders:
            messages.append("✅ GPU acceleration available")
        else:
            messages.append("❌ No GPU acceleration available")
        
        # OpenCL Status
        if self.opencl_support:
            messages.append("🔷 OpenCL support detected")
        else:
            messages.append("❌ OpenCL not available")
        
        if self.opencv_opencl:
            messages.append("✅ OpenCV OpenCL enabled")
        else:
            messages.append("⚠️  OpenCV OpenCL not available")
        
        # Hardware Encoders
        if self.hardware_encoders:
            encoders_str = ", ".join(self.hardware_encoders)
            messages.append(f"🎬 Supported hardware encoders: {encoders_str}")
        
        # Hardware Decoders
        if self.hardware_decoders:
            decoders_str = ", ".join(self.hardware_decoders)
            messages.append(f"🎞️ Supported hardware decoders: {decoders_str}")
        
        return messages

# Test function
if __name__ == "__main__":
    detector = GPUDetector()
    info = detector.detect_all()
    
    print("=== GPU Detection Results ===")
    for message in detector.get_status_messages():
        print(message)
    
    print("\n=== Recommended Settings ===")
    settings = info['recommended_settings']
    for key, value in settings.items():
        print(f"{key}: {value}")