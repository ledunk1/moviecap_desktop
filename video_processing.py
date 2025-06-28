import os
import numpy as np
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, CompositeVideoClip

class VideoProcessor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.cancelled = False
        
    def log(self, message):
        if self.progress_callback:
            self.progress_callback(message)
        print(message)
        
    def cancel(self):
        self.cancelled = True
        
    def get_end_segment(self, duration):
        """Calculate end segment based on video duration, ensuring last 10 seconds are included"""
        minutes = duration / 60
        if minutes <= 90:
            main_start = duration - 300  # 5 minutes before end
        elif minutes <= 120:
            main_start = duration - 480  # 8 minutes before end
        else:
            main_start = duration - 600  # 10 minutes before end
        
        final_segment_start = duration - 10
        final_segment_end = duration - 0.5
        return (main_start, final_segment_start, final_segment_end)

    def analyze_video_quality(self, video):
        """Analyze input video to determine quality settings"""
        height = video.h
        width = video.w
        pixels = width * height

        if pixels >= 8294400:  # 4K
            return '40000k'
        elif pixels >= 2073600:  # 1080p
            return '10000k'
        elif pixels >= 921600:  # 720p
            return '6000k'
        else:
            return '4000k'

    def validate_settings(self, settings):
        """Validate probability settings total 100%"""
        effect_total = sum(settings['effect_probs'].values())
        if not np.isclose(effect_total, 1.0):
            raise ValueError("Effect probabilities must total 100%")

        segment_total = sum(settings['segment_dist'].values())
        if not np.isclose(segment_total, 1.0):
            raise ValueError("Segment distribution must total 100%")

    def create_zoom_effect(self, clip, zoom_factor=1.3, duration=None):
        if duration is None:
            duration = clip.duration

        def zoom(t):
            progress = np.sin((t/3) * np.pi / duration) * (zoom_factor - 1) + 1
            return progress

        return clip.resize(zoom).crop(
            x_center=clip.w/2,
            y_center=clip.h/2,
            width=clip.w,
            height=clip.h
        )

    def create_freeze_frame_with_effects(self, clip, duration, settings):
        freeze_frame = clip.to_ImageClip(t=0)
        
        if random.random() < settings['freeze']['zoom_probability']:
            effect = self.create_zoom_effect(freeze_frame, zoom_factor=1.3, duration=duration)
        else:
            effect = freeze_frame
        
        return effect.set_duration(duration)

    def apply_fade_transition(self, clip, fade_duration):
        return clip.fadein(fade_duration).fadeout(fade_duration)

    def is_timestamp_excluded(self, time, excluded_timestamps):
        """Check if a timestamp falls within excluded ranges"""
        return any(start <= time <= end for start, end, _ in excluded_timestamps)

    def create_random_effect_clip(self, clip, start_time, duration, settings):
        if self.cancelled:
            return None
            
        if any(self.is_timestamp_excluded(t, settings['excluded_timestamps'])
               for t in np.arange(start_time, start_time + duration, 0.5)):
            return None

        subclip = clip.subclip(start_time, start_time + duration)
        
        effect_choices = ['slowmo', 'freeze', 'normal']
        weights = [settings['effect_probs']['slowmo'],
                  settings['effect_probs']['freeze'],
                  settings['effect_probs']['normal']]
        
        effect_type = random.choices(effect_choices, weights=weights)[0]
        
        if effect_type == "slowmo":
            effect_clip = subclip.fx(vfx.speedx, settings['slowmo_speed'])
        elif effect_type == "freeze":
            effect_clip = self.create_freeze_frame_with_effects(subclip, duration, settings)
        else:  # normal speed
            effect_clip = subclip
        
        if random.random() < settings['transition']['fade_probability']:
            effect_clip = self.apply_fade_transition(effect_clip, settings['transition']['fade_duration'])
        
        return effect_clip

    def create_section_clips(self, video, section_start, section_end, num_segments, settings):
        clips = []
        section_duration = section_end - section_start
        
        actual_segments = max(1, min(num_segments, int(section_duration / 2)))
        step = section_duration / actual_segments
        
        current_time = section_start
        while current_time < section_end and not self.cancelled:
            remaining_time = section_end - current_time
            if remaining_time < 2:
                break
                
            max_duration = min(4, remaining_time)
            segment_duration = random.uniform(2, max_duration)
            
            try:
                clip = self.create_random_effect_clip(video, current_time, segment_duration, settings)
                if clip is not None:
                    clips.append(clip)
                    
                    if random.random() < settings['repeat']['probability']:
                        num_repeats = random.randint(1, settings['repeat']['max_repeats'])
                        for _ in range(num_repeats):
                            if self.cancelled:
                                break
                            repeat_clip = self.create_random_effect_clip(video, current_time, segment_duration, settings)
                            if repeat_clip is not None:
                                clips.append(repeat_clip)
            except Exception as e:
                self.log(f"Error creating clip at {current_time}: {e}")
                
            step_variation = random.uniform(0.8, 1.2)
            current_time += step * step_variation
            
        return clips

    def create_included_segment_clips(self, video, include_timestamps, settings):
        """Create clips from specifically included timestamps"""
        included_clips = []

        for start, end, position in include_timestamps:
            if self.cancelled:
                break
                
            if position not in ['beginning', 'middle', 'end']:
                position = 'end'  # Default to end if invalid position

            try:
                duration = end - start
                if duration <= 0:
                    continue

                subclip = video.subclip(start, end)

                # Apply random effects to included clips
                effect_choices = ['slowmo', 'freeze', 'normal']
                weights = [settings['effect_probs']['slowmo'],
                          settings['effect_probs']['freeze'],
                          settings['effect_probs']['normal']]

                effect_type = random.choices(effect_choices, weights=weights)[0]

                if effect_type == "slowmo":
                    effect_clip = subclip.fx(vfx.speedx, settings['slowmo_speed'])
                elif effect_type == "freeze":
                    effect_clip = self.create_freeze_frame_with_effects(subclip, duration, settings)
                else:  # normal speed
                    effect_clip = subclip

                if random.random() < settings['transition']['fade_probability']:
                    effect_clip = self.apply_fade_transition(effect_clip, settings['transition']['fade_duration'])

                included_clips.append((effect_clip, position))

            except Exception as e:
                self.log(f"Error creating included clip at {start}-{end}: {e}")

        return included_clips

    def get_ffmpeg_params(self, settings):
        """Get FFmpeg parameters based on hardware acceleration settings"""
        params = {}
        
        if 'hardware_acceleration' in settings and settings['hardware_acceleration']['enabled']:
            encoder = settings['hardware_acceleration']['encoder']
            preset = settings['hardware_acceleration']['preset']
            
            params['codec'] = encoder
            
            # Set preset based on encoder type
            if 'nvenc' in encoder:
                # NVIDIA NVENC presets
                nvenc_presets = {
                    'ultrafast': 'p1', 'superfast': 'p2', 'veryfast': 'p3',
                    'faster': 'p4', 'fast': 'p4', 'medium': 'p5',
                    'slow': 'p6', 'slower': 'p7', 'veryslow': 'p7'
                }
                params['preset'] = nvenc_presets.get(preset, 'p4')
            elif 'qsv' in encoder:
                # Intel Quick Sync presets
                qsv_presets = {
                    'ultrafast': 'veryfast', 'superfast': 'veryfast', 'veryfast': 'veryfast',
                    'faster': 'faster', 'fast': 'fast', 'medium': 'medium',
                    'slow': 'slow', 'slower': 'slower', 'veryslow': 'veryslow'
                }
                params['preset'] = qsv_presets.get(preset, 'medium')
            elif 'amf' in encoder:
                # AMD AMF presets
                amf_presets = {
                    'ultrafast': 'speed', 'superfast': 'speed', 'veryfast': 'speed',
                    'faster': 'balanced', 'fast': 'balanced', 'medium': 'balanced',
                    'slow': 'quality', 'slower': 'quality', 'veryslow': 'quality'
                }
                params['preset'] = amf_presets.get(preset, 'balanced')
            else:
                params['preset'] = preset
        else:
            # Software encoding
            params['codec'] = 'libx264'
            params['preset'] = 'medium'
        
        return params

    def process_video(self, video_path, audio_path, output_path, settings):
        """Main video processing function"""
        try:
            self.log("Loading video and audio files...")
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            
            if self.cancelled:
                return False
            
            # Update settings
            settings['quality'] = {'bitrate': self.analyze_video_quality(video)}
            self.validate_settings(settings)
            
            video_duration = video.duration
            target_duration = audio.duration
            
            self.log(f"Video duration: {video_duration:.2f}s, Target duration: {target_duration:.2f}s")
            
            # Calculate video sections
            beginning_end = video_duration * 0.33
            middle_start = video_duration * 0.33
            middle_end = video_duration * 0.66
            main_start, final_start, final_end = self.get_end_segment(video_duration)
            
            # Calculate segments
            beginning_target = target_duration * settings['segment_dist']['beginning']
            middle_target = target_duration * settings['segment_dist']['middle']
            end_target = target_duration * settings['segment_dist']['end']
            
            avg_segment_duration = 3
            beginning_segments = int(beginning_target / avg_segment_duration)
            middle_segments = int(middle_target / avg_segment_duration)
            end_segments = int(end_target / avg_segment_duration)
            
            self.log("Creating video segments...")
            
            # Create clips
            beginning_clips = self.create_section_clips(video, 0, beginning_end, beginning_segments, settings)
            if self.cancelled:
                return False
                
            middle_clips = self.create_section_clips(video, middle_start, middle_end, middle_segments, settings)
            if self.cancelled:
                return False
                
            end_clips = self.create_section_clips(video, main_start, final_start, end_segments, settings)
            if self.cancelled:
                return False
            
            # Add final clip
            final_clip = video.subclip(final_start, final_end)
            end_clips.append(final_clip)
            
            # Create included segment clips
            self.log("Processing specifically included segments...")
            included_clips = self.create_included_segment_clips(video, settings['include_timestamps'], settings)
            if self.cancelled:
                return False
            
            # Organize all segments
            all_segments = beginning_clips + middle_clips + end_clips
            
            # Add specifically included clips at their specified positions
            included_end_clips = [clip for clip, position in included_clips if position == 'end']
            
            # Calculate total duration
            main_clips_duration = sum(clip.duration for clip in all_segments)
            included_clips_duration = sum(clip.duration for clip, _ in included_clips)
            
            # Trim if necessary
            if main_clips_duration + included_clips_duration > target_duration:
                trim_duration = main_clips_duration + included_clips_duration - target_duration
                while trim_duration > 0 and all_segments:
                    clip_to_remove = all_segments.pop()
                    trim_duration -= clip_to_remove.duration
            
            # Add included clips
            all_segments.extend(included_end_clips)
            
            if not all_segments:
                raise ValueError("No valid video segments could be created")
            
            if self.cancelled:
                return False
            
            self.log("Concatenating clips...")
            final_video = concatenate_videoclips(all_segments)
            final_video.fps = settings['fps']
            
            if final_video.duration > target_duration:
                final_video = final_video.subclip(0, target_duration)
            
            final_video = final_video.set_audio(audio)
            
            if self.cancelled:
                return False
            
            # Get FFmpeg parameters based on hardware acceleration settings
            ffmpeg_params = self.get_ffmpeg_params(settings)
            
            # Write final video
            self.log(f"Rendering final video with {ffmpeg_params['codec']} encoder...")
            
            write_params = {
                'codec': ffmpeg_params['codec'],
                'audio_codec': 'aac',
                'bitrate': settings['quality']['bitrate'],
                'preset': ffmpeg_params['preset'],
                'threads': 4,
                'fps': settings['fps']
            }
            
            # Log encoding settings
            self.log(f"Encoding settings: {write_params}")
            
            final_video.write_videofile(output_path, **write_params)
            
            # Cleanup
            video.close()
            audio.close()
            final_video.close()
            
            if self.cancelled:
                return False
            
            self.log(f"Video processing completed successfully! Output: {output_path}")
            return True
            
        except Exception as e:
            self.log(f"Error during processing: {str(e)}")
            return False