# Tool implementations
from .filesystem import (
    read_file, write_file, edit_file, delete_file,
    delete_directory, create_directory, move_file, copy_file,
    list_directory, FILESYSTEM_TOOLS
)
from .shell import run_command, SHELL_TOOLS
from .search import search_code, search_files, grep_count, SEARCH_TOOLS
from .spawn import spawn_research, spawn_single, SPAWN_TOOLS
from .image import (
    analyze_image, generate_image, generate_image_prompt,
    describe_for_accessibility, extract_text_from_image,
    detect_objects, compare_images, IMAGE_TOOLS
)
from .video import (
    analyze_video, describe_video_scene, extract_video_frames,
    transcribe_video, count_objects_in_video, detect_video_emotions,
    VIDEO_TOOLS
)
from .audio import (
    transcribe_audio, generate_speech, generate_dialogue,
    analyze_audio, translate_audio, extract_audio_segment,
    AUDIO_TOOLS
)
from .documents import (
    process_document, extract_tables, summarize_document,
    extract_form_data, compare_documents, analyze_spreadsheet,
    query_document_section, DOCUMENT_TOOLS
)
from .web import (
    web_search, fetch_url, fetch_multiple_urls, extract_links,
    scrape_structured_data, search_and_summarize,
    monitor_page_changes, verify_claim, WEB_TOOLS
)
from .code_execution import (
    execute_python, calculate, analyze_data, validate_code,
    solve_equation, run_simulation, generate_and_test, debug_code,
    CODE_EXECUTION_TOOLS
)
from .custom_loader import (
    load_custom_tools, get_custom_tools, create_default_config,
    list_custom_tools, CUSTOM_LOADER_TOOLS
)

__all__ = [
    # Filesystem
    'read_file', 'write_file', 'edit_file', 'delete_file',
    'delete_directory', 'create_directory', 'move_file', 'copy_file',
    'list_directory', 'FILESYSTEM_TOOLS',
    # Shell
    'run_command', 'SHELL_TOOLS',
    # Search
    'search_code', 'search_files', 'grep_count', 'SEARCH_TOOLS',
    # Spawn
    'spawn_research', 'spawn_single', 'SPAWN_TOOLS',
    # Image
    'analyze_image', 'generate_image', 'generate_image_prompt',
    'describe_for_accessibility', 'extract_text_from_image',
    'detect_objects', 'compare_images', 'IMAGE_TOOLS',
    # Video
    'analyze_video', 'describe_video_scene', 'extract_video_frames',
    'transcribe_video', 'count_objects_in_video', 'detect_video_emotions',
    'VIDEO_TOOLS',
    # Audio
    'transcribe_audio', 'generate_speech', 'generate_dialogue',
    'analyze_audio', 'translate_audio', 'extract_audio_segment',
    'AUDIO_TOOLS',
    # Documents
    'process_document', 'extract_tables', 'summarize_document',
    'extract_form_data', 'compare_documents', 'analyze_spreadsheet',
    'query_document_section', 'DOCUMENT_TOOLS',
    # Web
    'web_search', 'fetch_url', 'fetch_multiple_urls', 'extract_links',
    'scrape_structured_data', 'search_and_summarize',
    'monitor_page_changes', 'verify_claim', 'WEB_TOOLS',
    # Code Execution
    'execute_python', 'calculate', 'analyze_data', 'validate_code',
    'solve_equation', 'run_simulation', 'generate_and_test', 'debug_code',
    'CODE_EXECUTION_TOOLS',
    # Custom Tools
    'load_custom_tools', 'get_custom_tools', 'create_default_config',
    'list_custom_tools', 'CUSTOM_LOADER_TOOLS',
]
