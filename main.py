import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import json
import numpy as np
import random
import glob
from datetime import datetime
import queue

class VideoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Movie Recap Editor")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize variables
        self.video_file = None
        self.audio_file = None
        self.output_folder = "output"
        self.processing = False
        self.progress_queue = queue.Queue()
        self.gpu_info = None
        
        # Ensure output directory exists
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Default settings - Fixed the key name
        self.settings = {
            'effect_probs': {
                'slowmo': 0.25,
                'freeze': 0.65,
                'normal': 0.10
            },
            'segment_dist': {
                'beginning': 0.40,
                'middle': 0.25,
                'end': 0.35
            },
            'slowmo_speed': 0.35,
            'fps': 24,
            'transition': {
                'fade_probability': 0.5,
                'fade_duration': 0.5
            },
            'repeat': {
                'probability': 0.2,
                'max_repeats': 1
            },
            'freeze': {
                'zoom_probability': 0.3
            },
            'excluded_timestamps': [
                [0, 97, "Opening sequence"],
                [176, 206, "Scene transition"],
                [260, 280, "Scene transition"],
                [342, 357, "Scene transition"],
                [411, 442, "Scene transition"],
                [7522, 7642, "End sequence"],
                [7656, 7668, "Credits start"],
                [7773, 8138, "End credits"]
            ],
            'include_timestamps': [  # Fixed key name from 'include_timestamps'
                [7674, 7773, "end"]
            ],
            'hardware_acceleration': {
                'enabled': False,
                'encoder': 'libx264',
                'decoder': 'auto',
                'preset': 'medium'
            }
        }
        
        self.setup_ui()
        # Don't call load_files here since handlers aren't bound yet
        
    def setup_ui(self):
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # File Manager Tab
        self.setup_file_manager_tab()
        
        # Video Processing Tab
        self.setup_processing_tab()
        
        # Settings Tab
        self.setup_settings_tab()
        
        # GPU Info Tab
        self.setup_gpu_info_tab()
        
        # Progress Tab
        self.setup_progress_tab()
        
    def setup_file_manager_tab(self):
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="File Manager")
        
        # File list
        list_frame = ttk.LabelFrame(self.file_frame, text="Output Files", padding=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for file list
        columns = ('Name', 'Size', 'Modified')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=200)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # File operations buttons - Use lambda to avoid AttributeError during init
        button_frame = ttk.Frame(self.file_frame)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=lambda: self.load_files()).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Open File", command=lambda: self.open_selected_file()).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete File", command=lambda: self.delete_selected_file()).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Open Output Folder", command=lambda: self.open_output_folder()).pack(side='left', padx=5)
        
    def setup_processing_tab(self):
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="Video Processing")
        
        # File selection
        file_frame = ttk.LabelFrame(self.process_frame, text="File Selection", padding=10)
        file_frame.pack(fill='x', padx=10, pady=5)
        
        # Video file selection
        video_frame = ttk.Frame(file_frame)
        video_frame.pack(fill='x', pady=2)
        ttk.Label(video_frame, text="Video File:").pack(side='left')
        self.video_label = ttk.Label(video_frame, text="No file selected", foreground='gray')
        self.video_label.pack(side='left', padx=10)
        ttk.Button(video_frame, text="Browse", command=lambda: self.select_video_file()).pack(side='right')
        
        # Audio file selection
        audio_frame = ttk.Frame(file_frame)
        audio_frame.pack(fill='x', pady=2)
        ttk.Label(audio_frame, text="Audio File:").pack(side='left')
        self.audio_label = ttk.Label(audio_frame, text="No file selected", foreground='gray')
        self.audio_label.pack(side='left', padx=10)
        ttk.Button(audio_frame, text="Browse", command=lambda: self.select_audio_file()).pack(side='right')
        
        # Quick settings
        quick_frame = ttk.LabelFrame(self.process_frame, text="Quick Settings", padding=10)
        quick_frame.pack(fill='x', padx=10, pady=5)
        
        # FPS setting
        fps_frame = ttk.Frame(quick_frame)
        fps_frame.pack(fill='x', pady=2)
        ttk.Label(fps_frame, text="FPS:").pack(side='left')
        self.fps_var = tk.StringVar(value=str(self.settings['fps']))
        fps_spinbox = ttk.Spinbox(fps_frame, from_=1, to=60, textvariable=self.fps_var, width=10)
        fps_spinbox.pack(side='left', padx=10)
        
        # Slow motion speed
        slowmo_frame = ttk.Frame(quick_frame)
        slowmo_frame.pack(fill='x', pady=2)
        ttk.Label(slowmo_frame, text="Slow Motion Speed:").pack(side='left')
        self.slowmo_var = tk.StringVar(value=str(self.settings['slowmo_speed']))
        slowmo_spinbox = ttk.Spinbox(slowmo_frame, from_=0.1, to=1.0, increment=0.05, textvariable=self.slowmo_var, width=10)
        slowmo_spinbox.pack(side='left', padx=10)
        
        # Hardware acceleration settings
        hw_frame = ttk.LabelFrame(self.process_frame, text="Hardware Acceleration", padding=10)
        hw_frame.pack(fill='x', padx=10, pady=5)
        
        # Hardware acceleration enable/disable
        hw_enable_frame = ttk.Frame(hw_frame)
        hw_enable_frame.pack(fill='x', pady=2)
        self.hw_accel_var = tk.BooleanVar(value=self.settings['hardware_acceleration']['enabled'])
        ttk.Checkbutton(hw_enable_frame, text="Enable Hardware Acceleration", 
                       variable=self.hw_accel_var, command=self.on_hw_accel_toggle).pack(side='left')
        
        # Encoder selection
        encoder_frame = ttk.Frame(hw_frame)
        encoder_frame.pack(fill='x', pady=2)
        ttk.Label(encoder_frame, text="Encoder:").pack(side='left')
        self.encoder_var = tk.StringVar(value=self.settings['hardware_acceleration']['encoder'])
        self.encoder_combo = ttk.Combobox(encoder_frame, textvariable=self.encoder_var, 
                                         values=['libx264', 'h264_nvenc', 'h264_qsv', 'h264_amf', 'h264_videotoolbox'],
                                         state='readonly', width=15)
        self.encoder_combo.pack(side='left', padx=10)
        
        # Preset selection
        preset_frame = ttk.Frame(hw_frame)
        preset_frame.pack(fill='x', pady=2)
        ttk.Label(preset_frame, text="Preset:").pack(side='left')
        self.preset_var = tk.StringVar(value=self.settings['hardware_acceleration']['preset'])
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var,
                                        values=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
                                        state='readonly', width=15)
        self.preset_combo.pack(side='left', padx=10)
        
        # Auto-detect button
        detect_frame = ttk.Frame(hw_frame)
        detect_frame.pack(fill='x', pady=5)
        ttk.Button(detect_frame, text="🔍 Auto-Detect GPU", command=lambda: self.detect_gpu()).pack(side='left', padx=5)
        ttk.Button(detect_frame, text="📊 View GPU Info", command=lambda: self.show_gpu_tab()).pack(side='left', padx=5)
        
        # Process button
        process_frame = ttk.Frame(self.process_frame)
        process_frame.pack(fill='x', padx=10, pady=20)
        
        self.process_button = ttk.Button(process_frame, text="Generate Video", command=lambda: self.start_processing())
        self.process_button.pack(pady=10)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(process_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
    def setup_settings_tab(self):
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Advanced Settings")
        
        # Create main container frame
        main_container = ttk.Frame(self.settings_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create scrollable frame with improved setup
        self.canvas = tk.Canvas(main_container, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        
        # Bind mouse wheel scrolling
        self.bind_mousewheel()
        
        # Handle canvas resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Effect Probabilities
        effect_frame = ttk.LabelFrame(self.scrollable_frame, text="Effect Probabilities (Total must equal 1.0)", padding=10)
        effect_frame.pack(fill='x', padx=10, pady=5)
        
        self.effect_vars = {}
        effects = [('Slow Motion', 'slowmo'), ('Freeze', 'freeze'), ('Normal', 'normal')]
        
        for i, (label, key) in enumerate(effects):
            frame = ttk.Frame(effect_frame)
            frame.pack(fill='x', pady=2)
            # Fix: Create label with fixed width using configure
            label_widget = ttk.Label(frame, text=f"{label}:")
            label_widget.pack(side='left', anchor='w')
            label_widget.configure(width=15)
            var = tk.StringVar(value=str(self.settings['effect_probs'][key]))
            self.effect_vars[key] = var
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side='left', padx=10)
            entry.bind('<KeyRelease>', lambda e: self.update_effect_total())
        
        self.effect_total_var = tk.StringVar(value="Total: 1.00")
        ttk.Label(effect_frame, textvariable=self.effect_total_var, foreground='blue').pack(pady=5)
        
        # Segment Distribution
        segment_frame = ttk.LabelFrame(self.scrollable_frame, text="Segment Distribution (Total must equal 1.0)", padding=10)
        segment_frame.pack(fill='x', padx=10, pady=5)
        
        self.segment_vars = {}
        segments = [('Beginning', 'beginning'), ('Middle', 'middle'), ('End', 'end')]
        
        for label, key in segments:
            frame = ttk.Frame(segment_frame)
            frame.pack(fill='x', pady=2)
            # Fix: Create label with fixed width using configure
            label_widget = ttk.Label(frame, text=f"{label}:")
            label_widget.pack(side='left', anchor='w')
            label_widget.configure(width=15)
            var = tk.StringVar(value=str(self.settings['segment_dist'][key]))
            self.segment_vars[key] = var
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side='left', padx=10)
            entry.bind('<KeyRelease>', lambda e: self.update_segment_total())
        
        self.segment_total_var = tk.StringVar(value="Total: 1.00")
        ttk.Label(segment_frame, textvariable=self.segment_total_var, foreground='blue').pack(pady=5)
        
        # Transition Settings
        transition_frame = ttk.LabelFrame(self.scrollable_frame, text="Transition Settings", padding=10)
        transition_frame.pack(fill='x', padx=10, pady=5)
        
        # Fade probability
        fade_prob_frame = ttk.Frame(transition_frame)
        fade_prob_frame.pack(fill='x', pady=2)
        label_widget = ttk.Label(fade_prob_frame, text="Fade Probability:")
        label_widget.pack(side='left', anchor='w')
        label_widget.configure(width=20)
        self.fade_prob_var = tk.StringVar(value=str(self.settings['transition']['fade_probability']))
        ttk.Entry(fade_prob_frame, textvariable=self.fade_prob_var, width=10).pack(side='left', padx=10)
        
        # Fade duration
        fade_dur_frame = ttk.Frame(transition_frame)
        fade_dur_frame.pack(fill='x', pady=2)
        label_widget = ttk.Label(fade_dur_frame, text="Fade Duration:")
        label_widget.pack(side='left', anchor='w')
        label_widget.configure(width=20)
        self.fade_dur_var = tk.StringVar(value=str(self.settings['transition']['fade_duration']))
        ttk.Entry(fade_dur_frame, textvariable=self.fade_dur_var, width=10).pack(side='left', padx=10)
        
        # Repeat Settings
        repeat_frame = ttk.LabelFrame(self.scrollable_frame, text="Repeat Settings", padding=10)
        repeat_frame.pack(fill='x', padx=10, pady=5)
        
        # Repeat probability
        repeat_prob_frame = ttk.Frame(repeat_frame)
        repeat_prob_frame.pack(fill='x', pady=2)
        label_widget = ttk.Label(repeat_prob_frame, text="Repeat Probability:")
        label_widget.pack(side='left', anchor='w')
        label_widget.configure(width=20)
        self.repeat_prob_var = tk.StringVar(value=str(self.settings['repeat']['probability']))
        ttk.Entry(repeat_prob_frame, textvariable=self.repeat_prob_var, width=10).pack(side='left', padx=10)
        
        # Max repeats
        max_repeat_frame = ttk.Frame(repeat_frame)
        max_repeat_frame.pack(fill='x', pady=2)
        label_widget = ttk.Label(max_repeat_frame, text="Max Repeats:")
        label_widget.pack(side='left', anchor='w')
        label_widget.configure(width=20)
        self.max_repeat_var = tk.StringVar(value=str(self.settings['repeat']['max_repeats']))
        ttk.Entry(max_repeat_frame, textvariable=self.max_repeat_var, width=10).pack(side='left', padx=10)
        
        # Freeze Settings
        freeze_frame = ttk.LabelFrame(self.scrollable_frame, text="Freeze Frame Settings", padding=10)
        freeze_frame.pack(fill='x', padx=10, pady=5)
        
        zoom_prob_frame = ttk.Frame(freeze_frame)
        zoom_prob_frame.pack(fill='x', pady=2)
        label_widget = ttk.Label(zoom_prob_frame, text="Zoom Probability:")
        label_widget.pack(side='left', anchor='w')
        label_widget.configure(width=20)
        self.zoom_prob_var = tk.StringVar(value=str(self.settings['freeze']['zoom_probability']))
        ttk.Entry(zoom_prob_frame, textvariable=self.zoom_prob_var, width=10).pack(side='left', padx=10)
        
        # Timestamps section
        self.setup_timestamps_section(self.scrollable_frame)
        
        # Settings buttons
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save Settings", command=lambda: self.save_settings()).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Load Settings", command=lambda: self.load_settings()).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Reset to Default", command=lambda: self.reset_settings()).pack(side='left', padx=5)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")
        
    def setup_gpu_info_tab(self):
        """Setup GPU information tab"""
        self.gpu_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gpu_frame, text="GPU Info")
        
        # GPU Detection Status
        status_frame = ttk.LabelFrame(self.gpu_frame, text="GPU Detection Status", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        # Detection button
        detect_button_frame = ttk.Frame(status_frame)
        detect_button_frame.pack(fill='x', pady=5)
        
        ttk.Button(detect_button_frame, text="🔍 Detect GPU Hardware", 
                  command=lambda: self.detect_gpu()).pack(side='left', padx=5)
        ttk.Button(detect_button_frame, text="🔄 Refresh", 
                  command=lambda: self.refresh_gpu_info()).pack(side='left', padx=5)
        
        # Status display
        self.gpu_status_text = scrolledtext.ScrolledText(status_frame, height=8, state='disabled')
        self.gpu_status_text.pack(fill='both', expand=True, pady=5)
        
        # GPU Details
        details_frame = ttk.LabelFrame(self.gpu_frame, text="Hardware Details", padding=10)
        details_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview for GPU details
        columns = ('Property', 'Value')
        self.gpu_tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=12)
        self.gpu_tree.heading('Property', text='Property')
        self.gpu_tree.heading('Value', text='Value')
        self.gpu_tree.column('Property', width=200)
        self.gpu_tree.column('Value', width=400)
        
        # Scrollbar for GPU tree
        gpu_scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=self.gpu_tree.yview)
        self.gpu_tree.configure(yscrollcommand=gpu_scrollbar.set)
        
        self.gpu_tree.pack(side='left', fill='both', expand=True)
        gpu_scrollbar.pack(side='right', fill='y')
        
        # Recommended Settings
        rec_frame = ttk.LabelFrame(self.gpu_frame, text="Recommended Settings", padding=10)
        rec_frame.pack(fill='x', padx=10, pady=5)
        
        self.rec_settings_text = scrolledtext.ScrolledText(rec_frame, height=6, state='disabled')
        self.rec_settings_text.pack(fill='both', expand=True, pady=5)
        
        # Apply recommended settings button
        apply_frame = ttk.Frame(rec_frame)
        apply_frame.pack(fill='x', pady=5)
        
        ttk.Button(apply_frame, text="✅ Apply Recommended Settings", 
                  command=lambda: self.apply_recommended_settings()).pack(side='left', padx=5)
        
    def bind_mousewheel(self):
        """Bind mouse wheel events for scrolling"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        # Bind mouse wheel when entering the canvas area
        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # Also bind to the scrollable frame
        self.scrollable_frame.bind('<Enter>', _bind_to_mousewheel)
        self.scrollable_frame.bind('<Leave>', _unbind_from_mousewheel)
    
    def on_canvas_configure(self, event):
        """Handle canvas resize to adjust scrollable frame width"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
    def setup_timestamps_section(self, parent):
        # Excluded Timestamps
        excluded_frame = ttk.LabelFrame(parent, text="Excluded Timestamps", padding=10)
        excluded_frame.pack(fill='x', padx=10, pady=5)
        
        # Create frame for treeview and scrollbar
        excluded_tree_frame = ttk.Frame(excluded_frame)
        excluded_tree_frame.pack(fill='both', expand=True, pady=5)
        
        self.excluded_tree = ttk.Treeview(excluded_tree_frame, columns=('Start', 'End', 'Description'), show='headings', height=6)
        self.excluded_tree.heading('Start', text='Start')
        self.excluded_tree.heading('End', text='End')
        self.excluded_tree.heading('Description', text='Description')
        
        # Add scrollbar for excluded timestamps
        excluded_scrollbar = ttk.Scrollbar(excluded_tree_frame, orient='vertical', command=self.excluded_tree.yview)
        self.excluded_tree.configure(yscrollcommand=excluded_scrollbar.set)
        
        self.excluded_tree.pack(side='left', fill='both', expand=True)
        excluded_scrollbar.pack(side='right', fill='y')
        
        excluded_buttons = ttk.Frame(excluded_frame)
        excluded_buttons.pack(fill='x')
        ttk.Button(excluded_buttons, text="Add", command=lambda: self.add_excluded_timestamp()).pack(side='left', padx=2)
        ttk.Button(excluded_buttons, text="Edit", command=lambda: self.edit_excluded_timestamp()).pack(side='left', padx=2)
        ttk.Button(excluded_buttons, text="Remove", command=lambda: self.remove_excluded_timestamp()).pack(side='left', padx=2)
        
        # Included Timestamps
        included_frame = ttk.LabelFrame(parent, text="Included Timestamps", padding=10)
        included_frame.pack(fill='x', padx=10, pady=5)
        
        # Create frame for treeview and scrollbar
        included_tree_frame = ttk.Frame(included_frame)
        included_tree_frame.pack(fill='both', expand=True, pady=5)
        
        self.included_tree = ttk.Treeview(included_tree_frame, columns=('Start', 'End', 'Position'), show='headings', height=6)
        self.included_tree.heading('Start', text='Start')
        self.included_tree.heading('End', text='End')
        self.included_tree.heading('Position', text='Position')
        
        # Add scrollbar for included timestamps
        included_scrollbar = ttk.Scrollbar(included_tree_frame, orient='vertical', command=self.included_tree.yview)
        self.included_tree.configure(yscrollcommand=included_scrollbar.set)
        
        self.included_tree.pack(side='left', fill='both', expand=True)
        included_scrollbar.pack(side='right', fill='y')
        
        included_buttons = ttk.Frame(included_frame)
        included_buttons.pack(fill='x')
        ttk.Button(included_buttons, text="Add", command=lambda: self.add_included_timestamp()).pack(side='left', padx=2)
        ttk.Button(included_buttons, text="Edit", command=lambda: self.edit_included_timestamp()).pack(side='left', padx=2)
        ttk.Button(included_buttons, text="Remove", command=lambda: self.remove_included_timestamp()).pack(side='left', padx=2)
        
        # Don't call populate_timestamp_trees here since handlers aren't bound yet
        
    def setup_progress_tab(self):
        self.progress_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.progress_frame, text="Progress")
        
        # Progress bar
        progress_frame = ttk.LabelFrame(self.progress_frame, text="Processing Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self.progress_frame, text="Processing Log", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state='disabled')
        self.log_text.pack(fill='both', expand=True)
        
        # Control buttons
        control_frame = ttk.Frame(self.progress_frame)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.cancel_button = ttk.Button(control_frame, text="Cancel Processing", command=lambda: self.cancel_processing(), state='disabled')
        self.cancel_button.pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="Clear Log", command=lambda: self.clear_log()).pack(side='left', padx=5)
        
    def on_hw_accel_toggle(self):
        """Handle hardware acceleration toggle"""
        if self.hw_accel_var.get():
            # Enable hardware acceleration
            self.encoder_combo.config(state='readonly')
            self.preset_combo.config(state='readonly')
        else:
            # Disable hardware acceleration
            self.encoder_var.set('libx264')
            self.encoder_combo.config(state='disabled')
            self.preset_combo.config(state='disabled')
    
    def detect_gpu(self):
        """Detect GPU and update settings"""
        def detection_thread():
            try:
                from gpu_detector import GPUDetector
                detector = GPUDetector()
                self.gpu_info = detector.detect_all()
                
                # Update UI in main thread
                self.root.after(0, self.update_gpu_display)
                
            except ImportError:
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    "GPU detection module not available. Please ensure all dependencies are installed."))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    f"GPU detection failed: {str(e)}"))
        
        # Show detection in progress
        self.status_var.set("Detecting GPU hardware...")
        
        # Start detection thread
        thread = threading.Thread(target=detection_thread)
        thread.daemon = True
        thread.start()
    
    def update_gpu_display(self):
        """Update GPU information display"""
        if not self.gpu_info:
            return
        
        # Update status text
        self.gpu_status_text.config(state='normal')
        self.gpu_status_text.delete(1.0, 'end')
        
        from gpu_detector import GPUDetector
        detector = GPUDetector()
        detector.gpu_info = self.gpu_info['gpus']
        detector.hardware_encoders = self.gpu_info['hardware_encoders']
        detector.hardware_decoders = self.gpu_info['hardware_decoders']
        detector.opencl_support = self.gpu_info['opencl_support']
        detector.opencv_opencl = self.gpu_info['opencv_opencl']
        
        status_messages = detector.get_status_messages()
        for message in status_messages:
            self.gpu_status_text.insert('end', message + '\n')
        
        self.gpu_status_text.config(state='disabled')
        
        # Update GPU details tree
        self.gpu_tree.delete(*self.gpu_tree.get_children())
        
        # Add GPU information
        for gpu_type, gpu_data in self.gpu_info['gpus'].items():
            parent = self.gpu_tree.insert('', 'end', text=gpu_type.upper(), 
                                         values=(f"{gpu_type.upper()} GPU", ""))
            for key, value in gpu_data.items():
                self.gpu_tree.insert(parent, 'end', values=(f"  {key.title()}", str(value)))
        
        # Add hardware encoders
        if self.gpu_info['hardware_encoders']:
            encoders_parent = self.gpu_tree.insert('', 'end', values=("Hardware Encoders", ""))
            for encoder in self.gpu_info['hardware_encoders']:
                self.gpu_tree.insert(encoders_parent, 'end', values=(f"  {encoder}", "Available"))
        
        # Add hardware decoders
        if self.gpu_info['hardware_decoders']:
            decoders_parent = self.gpu_tree.insert('', 'end', values=("Hardware Decoders", ""))
            for decoder in self.gpu_info['hardware_decoders']:
                self.gpu_tree.insert(decoders_parent, 'end', values=(f"  {decoder}", "Available"))
        
        # Add OpenCL info
        opencl_parent = self.gpu_tree.insert('', 'end', values=("OpenCL Support", ""))
        self.gpu_tree.insert(opencl_parent, 'end', values=("  System OpenCL", 
                            "Available" if self.gpu_info['opencl_support'] else "Not Available"))
        self.gpu_tree.insert(opencl_parent, 'end', values=("  OpenCV OpenCL", 
                            "Available" if self.gpu_info['opencv_opencl'] else "Not Available"))
        
        # Update recommended settings display
        self.rec_settings_text.config(state='normal')
        self.rec_settings_text.delete(1.0, 'end')
        
        rec_settings = self.gpu_info['recommended_settings']
        self.rec_settings_text.insert('end', "Recommended Settings Based on Detected Hardware:\n\n")
        for key, value in rec_settings.items():
            self.rec_settings_text.insert('end', f"{key.replace('_', ' ').title()}: {value}\n")
        
        self.rec_settings_text.config(state='disabled')
        
        self.status_var.set("GPU detection completed")
    
    def apply_recommended_settings(self):
        """Apply recommended GPU settings"""
        if not self.gpu_info or 'recommended_settings' not in self.gpu_info:
            messagebox.showwarning("Warning", "No GPU information available. Please detect GPU first.")
            return
        
        rec_settings = self.gpu_info['recommended_settings']
        
        # Apply settings
        if rec_settings['hardware_acceleration']:
            self.hw_accel_var.set(True)
            self.encoder_var.set(rec_settings['encoder'])
            self.preset_var.set(rec_settings['preset'])
            self.encoder_combo.config(state='readonly')
            self.preset_combo.config(state='readonly')
        else:
            self.hw_accel_var.set(False)
            self.encoder_var.set('libx264')
            self.preset_var.set('medium')
            self.encoder_combo.config(state='disabled')
            self.preset_combo.config(state='disabled')
        
        # Update settings dictionary
        self.settings['hardware_acceleration'] = {
            'enabled': rec_settings['hardware_acceleration'],
            'encoder': rec_settings['encoder'],
            'decoder': rec_settings['decoder'],
            'preset': rec_settings['preset']
        }
        
        messagebox.showinfo("Success", "Recommended settings have been applied!")
    
    def refresh_gpu_info(self):
        """Refresh GPU information"""
        self.detect_gpu()
    
    def show_gpu_tab(self):
        """Switch to GPU info tab"""
        self.notebook.select(3)  # GPU Info tab index
        if not self.gpu_info:
            self.detect_gpu()
        
    # Placeholder methods that will be overridden by handlers
    def load_files(self): pass
    def open_selected_file(self): pass
    def delete_selected_file(self): pass
    def open_output_folder(self): pass
    def select_video_file(self): pass
    def select_audio_file(self): pass
    def update_effect_total(self): pass
    def update_segment_total(self): pass
    def populate_timestamp_trees(self): pass
    def add_excluded_timestamp(self): pass
    def edit_excluded_timestamp(self): pass
    def remove_excluded_timestamp(self): pass
    def add_included_timestamp(self): pass
    def edit_included_timestamp(self): pass
    def remove_included_timestamp(self): pass
    def save_settings(self): pass
    def load_settings(self): pass
    def reset_settings(self): pass
    def start_processing(self): pass
    def cancel_processing(self): pass
    def clear_log(self): pass