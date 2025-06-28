import tkinter as tk
from tkinter import ttk
from main import VideoEditorApp
from ui_handlers import UIHandlers

class VideoEditorAppWithHandlers(VideoEditorApp):
    def __init__(self, root):
        # Initialize handlers first
        self.handlers = UIHandlers(self)
        # Then call parent init
        super().__init__(root)
        # Finally bind handlers and initialize UI data
        self.bind_handlers()
        self.initialize_ui_data()
        
    def bind_handlers(self):
        """Bind UI handlers to the application"""
        # File manager methods
        self.load_files = self.handlers.load_files
        self.open_selected_file = self.handlers.open_selected_file
        self.delete_selected_file = self.handlers.delete_selected_file
        self.open_output_folder = self.handlers.open_output_folder
        
        # File selection methods
        self.select_video_file = self.handlers.select_video_file
        self.select_audio_file = self.handlers.select_audio_file
        
        # Settings methods
        self.update_effect_total = self.handlers.update_effect_total
        self.update_segment_total = self.handlers.update_segment_total
        self.populate_timestamp_trees = self.handlers.populate_timestamp_trees
        
        # Timestamp methods
        self.add_excluded_timestamp = self.handlers.add_excluded_timestamp
        self.edit_excluded_timestamp = self.handlers.edit_excluded_timestamp
        self.remove_excluded_timestamp = self.handlers.remove_excluded_timestamp
        self.add_included_timestamp = self.handlers.add_included_timestamp
        self.edit_included_timestamp = self.handlers.edit_included_timestamp
        self.remove_included_timestamp = self.handlers.remove_included_timestamp
        
        # Settings file operations
        self.save_settings = self.handlers.save_settings
        self.load_settings = self.handlers.load_settings
        self.reset_settings = self.handlers.reset_settings
        
        # Processing methods
        self.start_processing = self.handlers.start_processing
        self.cancel_processing = self.handlers.cancel_processing
        self.clear_log = self.handlers.clear_log

    def initialize_ui_data(self):
        """Initialize UI data after handlers are bound"""
        self.load_files()
        self.populate_timestamp_trees()
        self.update_effect_total()
        self.update_segment_total()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorAppWithHandlers(root)
    root.mainloop()