import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import json
import subprocess
import platform
from datetime import datetime
from video_processing import VideoProcessor

class UIHandlers:
    def __init__(self, app):
        self.app = app
        self.processor = None
        
    def load_files(self):
        """Load files from output directory"""
        self.app.file_tree.delete(*self.app.file_tree.get_children())
        
        try:
            for filename in os.listdir(self.app.output_folder):
                filepath = os.path.join(self.app.output_folder, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    modified = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                    size_str = self.format_file_size(size)
                    self.app.file_tree.insert('', 'end', values=(filename, size_str, modified))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load files: {str(e)}")
    
    def format_file_size(self, bytes_size):
        """Format file size in human readable format"""
        units = ['B', 'KB', 'MB', 'GB']
        size = bytes_size
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    def open_selected_file(self):
        """Open selected file with default application"""
        selection = self.app.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = self.app.file_tree.item(selection[0])
        filename = item['values'][0]
        filepath = os.path.join(self.app.output_folder, filename)
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', filepath))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(filepath)
            else:  # Linux
                subprocess.call(('xdg-open', filepath))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def delete_selected_file(self):
        """Delete selected file"""
        selection = self.app.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = self.app.file_tree.item(selection[0])
        filename = item['values'][0]
        filepath = os.path.join(self.app.output_folder, filename)
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{filename}'?"):
            try:
                os.remove(filepath)
                self.load_files()
                messagebox.showinfo("Success", "File deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {str(e)}")
    
    def open_output_folder(self):
        """Open output folder in file explorer"""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', self.app.output_folder))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(self.app.output_folder)
            else:  # Linux
                subprocess.call(('xdg-open', self.app.output_folder))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
    
    def select_video_file(self):
        """Select video file"""
        filetypes = [
            ('Video files', '*.mp4 *.avi *.mov *.mkv *.wmv *.flv'),
            ('All files', '*.*')
        ]
        filename = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if filename:
            self.app.video_file = filename
            self.app.video_label.config(text=os.path.basename(filename), foreground='black')
    
    def select_audio_file(self):
        """Select audio file"""
        filetypes = [
            ('Audio files', '*.mp3 *.wav *.aac *.m4a *.ogg'),
            ('All files', '*.*')
        ]
        filename = filedialog.askopenfilename(title="Select Audio File", filetypes=filetypes)
        if filename:
            self.app.audio_file = filename
            self.app.audio_label.config(text=os.path.basename(filename), foreground='black')
    
    def update_effect_total(self, event=None):
        """Update effect probabilities total"""
        try:
            total = sum(float(var.get()) for var in self.app.effect_vars.values())
            color = 'green' if abs(total - 1.0) < 0.01 else 'red'
            self.app.effect_total_var.set(f"Total: {total:.2f}")
            # Update label color would require recreating the label
        except ValueError:
            self.app.effect_total_var.set("Total: Invalid")
    
    def update_segment_total(self, event=None):
        """Update segment distribution total"""
        try:
            total = sum(float(var.get()) for var in self.app.segment_vars.values())
            color = 'green' if abs(total - 1.0) < 0.01 else 'red'
            self.app.segment_total_var.set(f"Total: {total:.2f}")
        except ValueError:
            self.app.segment_total_var.set("Total: Invalid")
    
    def populate_timestamp_trees(self):
        """Populate timestamp trees with current settings"""
        # Clear existing items
        self.app.excluded_tree.delete(*self.app.excluded_tree.get_children())
        self.app.included_tree.delete(*self.app.included_tree.get_children())
        
        # Populate excluded timestamps
        for start, end, desc in self.app.settings['excluded_timestamps']:
            self.app.excluded_tree.insert('', 'end', values=(start, end, desc))
        
        # Populate included timestamps
        for start, end, pos in self.app.settings['include_timestamps']:
            self.app.included_tree.insert('', 'end', values=(start, end, pos))
    
    def add_excluded_timestamp(self):
        """Add new excluded timestamp"""
        dialog = TimestampDialog(self.app.root, "Add Excluded Timestamp")
        if dialog.result:
            start, end, desc = dialog.result
            self.app.settings['excluded_timestamps'].append([start, end, desc])
            self.populate_timestamp_trees()
    
    def edit_excluded_timestamp(self):
        """Edit selected excluded timestamp"""
        selection = self.app.excluded_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a timestamp first")
            return
        
        item = self.app.excluded_tree.item(selection[0])
        values = item['values']
        
        dialog = TimestampDialog(self.app.root, "Edit Excluded Timestamp", 
                               (values[0], values[1], values[2]))
        if dialog.result:
            index = self.app.excluded_tree.index(selection[0])
            start, end, desc = dialog.result
            self.app.settings['excluded_timestamps'][index] = [start, end, desc]
            self.populate_timestamp_trees()
    
    def remove_excluded_timestamp(self):
        """Remove selected excluded timestamp"""
        selection = self.app.excluded_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a timestamp first")
            return
        
        if messagebox.askyesno("Confirm", "Remove selected timestamp?"):
            index = self.app.excluded_tree.index(selection[0])
            del self.app.settings['excluded_timestamps'][index]
            self.populate_timestamp_trees()
    
    def add_included_timestamp(self):
        """Add new included timestamp"""
        dialog = IncludedTimestampDialog(self.app.root, "Add Included Timestamp")
        if dialog.result:
            start, end, pos = dialog.result
            self.app.settings['include_timestamps'].append([start, end, pos])
            self.populate_timestamp_trees()
    
    def edit_included_timestamp(self):
        """Edit selected included timestamp"""
        selection = self.app.included_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a timestamp first")
            return
        
        item = self.app.included_tree.item(selection[0])
        values = item['values']
        
        dialog = IncludedTimestampDialog(self.app.root, "Edit Included Timestamp", 
                                       (values[0], values[1], values[2]))
        if dialog.result:
            index = self.app.included_tree.index(selection[0])
            start, end, pos = dialog.result
            self.app.settings['include_timestamps'][index] = [start, end, pos]
            self.populate_timestamp_trees()
    
    def remove_included_timestamp(self):
        """Remove selected included timestamp"""
        selection = self.app.included_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a timestamp first")
            return
        
        if messagebox.askyesno("Confirm", "Remove selected timestamp?"):
            index = self.app.included_tree.index(selection[0])
            del self.app.settings['include_timestamps'][index]
            self.populate_timestamp_trees()
    
    def save_settings(self):
        """Save current settings to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.collect_settings()
                with open(filename, 'w') as f:
                    json.dump(self.app.settings, f, indent=2)
                messagebox.showinfo("Success", "Settings saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_settings(self):
        """Load settings from file"""
        filename = filedialog.askopenfilename(
            title="Load Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.app.settings = json.load(f)
                self.update_ui_from_settings()
                messagebox.showinfo("Success", "Settings loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to default"""
        if messagebox.askyesno("Confirm", "Reset all settings to default values?"):
            self.app.settings = {
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
                'include_timestamps': [
                    [7674, 7773, "end"]
                ],
                'hardware_acceleration': {
                    'enabled': False,
                    'encoder': 'libx264',
                    'decoder': 'auto',
                    'preset': 'medium'
                }
            }
            self.update_ui_from_settings()
    
    def collect_settings(self):
        """Collect settings from UI elements"""
        try:
            # Update settings from UI
            self.app.settings['fps'] = int(self.app.fps_var.get())
            self.app.settings['slowmo_speed'] = float(self.app.slowmo_var.get())
            
            # Effect probabilities
            for key, var in self.app.effect_vars.items():
                self.app.settings['effect_probs'][key] = float(var.get())
            
            # Segment distribution
            for key, var in self.app.segment_vars.items():
                self.app.settings['segment_dist'][key] = float(var.get())
            
            # Transition settings
            self.app.settings['transition']['fade_probability'] = float(self.app.fade_prob_var.get())
            self.app.settings['transition']['fade_duration'] = float(self.app.fade_dur_var.get())
            
            # Repeat settings
            self.app.settings['repeat']['probability'] = float(self.app.repeat_prob_var.get())
            self.app.settings['repeat']['max_repeats'] = int(self.app.max_repeat_var.get())
            
            # Freeze settings
            self.app.settings['freeze']['zoom_probability'] = float(self.app.zoom_prob_var.get())
            
            # Hardware acceleration settings
            self.app.settings['hardware_acceleration']['enabled'] = self.app.hw_accel_var.get()
            self.app.settings['hardware_acceleration']['encoder'] = self.app.encoder_var.get()
            self.app.settings['hardware_acceleration']['preset'] = self.app.preset_var.get()
            
        except ValueError as e:
            raise ValueError(f"Invalid setting value: {str(e)}")
    
    def update_ui_from_settings(self):
        """Update UI elements from current settings"""
        # Update basic settings
        self.app.fps_var.set(str(self.app.settings['fps']))
        self.app.slowmo_var.set(str(self.app.settings['slowmo_speed']))
        
        # Update effect probabilities
        for key, var in self.app.effect_vars.items():
            var.set(str(self.app.settings['effect_probs'][key]))
        
        # Update segment distribution
        for key, var in self.app.segment_vars.items():
            var.set(str(self.app.settings['segment_dist'][key]))
        
        # Update transition settings
        self.app.fade_prob_var.set(str(self.app.settings['transition']['fade_probability']))
        self.app.fade_dur_var.set(str(self.app.settings['transition']['fade_duration']))
        
        # Update repeat settings
        self.app.repeat_prob_var.set(str(self.app.settings['repeat']['probability']))
        self.app.max_repeat_var.set(str(self.app.settings['repeat']['max_repeats']))
        
        # Update freeze settings
        self.app.zoom_prob_var.set(str(self.app.settings['freeze']['zoom_probability']))
        
        # Update hardware acceleration settings
        if 'hardware_acceleration' in self.app.settings:
            self.app.hw_accel_var.set(self.app.settings['hardware_acceleration']['enabled'])
            self.app.encoder_var.set(self.app.settings['hardware_acceleration']['encoder'])
            self.app.preset_var.set(self.app.settings['hardware_acceleration']['preset'])
            
            # Update UI state based on hardware acceleration setting
            if self.app.settings['hardware_acceleration']['enabled']:
                self.app.encoder_combo.config(state='readonly')
                self.app.preset_combo.config(state='readonly')
            else:
                self.app.encoder_combo.config(state='disabled')
                self.app.preset_combo.config(state='disabled')
        
        # Update timestamp trees
        self.populate_timestamp_trees()
        
        # Update totals
        self.update_effect_total()
        self.update_segment_total()
    
    def start_processing(self):
        """Start video processing in background thread"""
        if not self.app.video_file or not self.app.audio_file:
            messagebox.showerror("Error", "Please select both video and audio files")
            return
        
        if self.app.processing:
            messagebox.showwarning("Warning", "Processing is already in progress")
            return
        
        try:
            self.collect_settings()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid settings: {str(e)}")
            return
        
        # Validate probabilities
        effect_total = sum(self.app.settings['effect_probs'].values())
        segment_total = sum(self.app.settings['segment_dist'].values())
        
        if abs(effect_total - 1.0) > 0.01 or abs(segment_total - 1.0) > 0.01:
            messagebox.showerror("Error", "Probability totals must equal 1.0")
            return
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"output_{timestamp}.mp4"
        output_path = os.path.join(self.app.output_folder, output_filename)
        
        # Start processing
        self.app.processing = True
        self.app.process_button.config(state='disabled')
        self.app.cancel_button.config(state='normal')
        self.app.progress_bar.start()
        self.app.notebook.select(4)  # Switch to progress tab (now index 4 due to GPU tab)
        
        # Create processor
        self.processor = VideoProcessor(self.log_message)
        
        # Start processing thread
        thread = threading.Thread(
            target=self.process_video_thread,
            args=(self.app.video_file, self.app.audio_file, output_path, self.app.settings.copy())
        )
        thread.daemon = True
        thread.start()
    
    def process_video_thread(self, video_path, audio_path, output_path, settings):
        """Video processing thread"""
        try:
            success = self.processor.process_video(video_path, audio_path, output_path, settings)
            
            # Update UI in main thread
            self.app.root.after(0, self.processing_complete, success, output_path)
            
        except Exception as e:
            self.app.root.after(0, self.processing_error, str(e))
    
    def processing_complete(self, success, output_path):
        """Called when processing is complete"""
        self.app.processing = False
        self.app.process_button.config(state='normal')
        self.app.cancel_button.config(state='disabled')
        self.app.progress_bar.stop()
        
        if success and not self.processor.cancelled:
            self.app.status_var.set("Processing completed successfully!")
            messagebox.showinfo("Success", f"Video processing completed!\nOutput: {os.path.basename(output_path)}")
            self.load_files()
        elif self.processor.cancelled:
            self.app.status_var.set("Processing cancelled")
            # Clean up partial output file
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
        else:
            self.app.status_var.set("Processing failed")
            messagebox.showerror("Error", "Video processing failed. Check the log for details.")
    
    def processing_error(self, error_message):
        """Called when processing encounters an error"""
        self.app.processing = False
        self.app.process_button.config(state='normal')
        self.app.cancel_button.config(state='disabled')
        self.app.progress_bar.stop()
        self.app.status_var.set("Processing failed")
        messagebox.showerror("Error", f"Processing failed: {error_message}")
    
    def cancel_processing(self):
        """Cancel current processing"""
        if self.processor and self.app.processing:
            if messagebox.askyesno("Confirm", "Are you sure you want to cancel processing?"):
                self.processor.cancel()
                self.log_message("Processing cancelled by user")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.app.log_text.config(state='normal')
        self.app.log_text.insert('end', log_entry)
        self.app.log_text.see('end')
        self.app.log_text.config(state='disabled')
        
        # Update progress label
        self.app.progress_var.set(message)
    
    def clear_log(self):
        """Clear the log"""
        self.app.log_text.config(state='normal')
        self.app.log_text.delete(1.0, 'end')
        self.app.log_text.config(state='disabled')


class TimestampDialog:
    def __init__(self, parent, title, initial_values=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Create form
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Start time
        ttk.Label(frame, text="Start Time (seconds):").grid(row=0, column=0, sticky='w', pady=5)
        self.start_var = tk.StringVar(value=str(initial_values[0]) if initial_values else "0")
        ttk.Entry(frame, textvariable=self.start_var, width=20).grid(row=0, column=1, pady=5)
        
        # End time
        ttk.Label(frame, text="End Time (seconds):").grid(row=1, column=0, sticky='w', pady=5)
        self.end_var = tk.StringVar(value=str(initial_values[1]) if initial_values else "0")
        ttk.Entry(frame, textvariable=self.end_var, width=20).grid(row=1, column=1, pady=5)
        
        # Description
        ttk.Label(frame, text="Description:").grid(row=2, column=0, sticky='w', pady=5)
        self.desc_var = tk.StringVar(value=str(initial_values[2]) if initial_values else "")
        ttk.Entry(frame, textvariable=self.desc_var, width=20).grid(row=2, column=1, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side='left', padx=5)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok_clicked(self):
        try:
            start = float(self.start_var.get())
            end = float(self.end_var.get())
            desc = self.desc_var.get()
            
            if start >= end:
                messagebox.showerror("Error", "Start time must be less than end time")
                return
            
            self.result = (start, end, desc)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for times")
    
    def cancel_clicked(self):
        self.dialog.destroy()


class IncludedTimestampDialog:
    def __init__(self, parent, title, initial_values=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Create form
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Start time
        ttk.Label(frame, text="Start Time (seconds):").grid(row=0, column=0, sticky='w', pady=5)
        self.start_var = tk.StringVar(value=str(initial_values[0]) if initial_values else "0")
        ttk.Entry(frame, textvariable=self.start_var, width=20).grid(row=0, column=1, pady=5)
        
        # End time
        ttk.Label(frame, text="End Time (seconds):").grid(row=1, column=0, sticky='w', pady=5)
        self.end_var = tk.StringVar(value=str(initial_values[1]) if initial_values else "0")
        ttk.Entry(frame, textvariable=self.end_var, width=20).grid(row=1, column=1, pady=5)
        
        # Position
        ttk.Label(frame, text="Position:").grid(row=2, column=0, sticky='w', pady=5)
        self.pos_var = tk.StringVar(value=str(initial_values[2]) if initial_values else "end")
        pos_combo = ttk.Combobox(frame, textvariable=self.pos_var, values=['beginning', 'middle', 'end'], width=17)
        pos_combo.grid(row=2, column=1, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side='left', padx=5)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok_clicked(self):
        try:
            start = float(self.start_var.get())
            end = float(self.end_var.get())
            pos = self.pos_var.get()
            
            if start >= end:
                messagebox.showerror("Error", "Start time must be less than end time")
                return
            
            if pos not in ['beginning', 'middle', 'end']:
                messagebox.showerror("Error", "Position must be beginning, middle, or end")
                return
            
            self.result = (start, end, pos)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for times")
    
    def cancel_clicked(self):
        self.dialog.destroy()