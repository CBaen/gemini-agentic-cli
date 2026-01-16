# Integration modules
from .security import (
    initialize_security,
    validate_path,
    validate_command,
    check_file_operation,
    check_command,
    set_confirmation_callback,
    request_confirmation,
)
from .session import (
    start_session,
    end_session,
    update_session,
    get_current_session,
    check_for_crash,
    read_handoff,
    write_handoff,
    read_memory,
    append_to_memory,
)
from .qdrant_client import (
    query_qdrant,
    store_to_qdrant,
    query_research,
    store_research,
    check_qdrant_available,
    QDRANT_TOOLS,
)
from .claude_collab import (
    check_turn,
    signal_claude_turn,
    signal_gemini_turn,
    read_handoff_context,
    add_to_shared_memory,
    create_research_handoff,
    COLLAB_TOOLS,
)
from .audit import (
    log_event,
    log_session_start,
    log_session_end,
    log_security_event,
    log_error,
    get_session_stats,
    search_logs,
    export_logs,
    audit_tool,
    audit_context,
    AUDIT_TOOLS,
)
from .ide_server import (
    start_ide_server,
    get_extension_template,
    IDEHandler,
    JSONRPCServer,
    IDE_SERVER_TOOLS,
)

__all__ = [
    # Security
    'initialize_security',
    'validate_path',
    'validate_command',
    'check_file_operation',
    'check_command',
    'set_confirmation_callback',
    'request_confirmation',
    # Session
    'start_session',
    'end_session',
    'update_session',
    'get_current_session',
    'check_for_crash',
    'read_handoff',
    'write_handoff',
    'read_memory',
    'append_to_memory',
    # Qdrant
    'query_qdrant',
    'store_to_qdrant',
    'query_research',
    'store_research',
    'check_qdrant_available',
    'QDRANT_TOOLS',
    # Claude Collaboration
    'check_turn',
    'signal_claude_turn',
    'signal_gemini_turn',
    'read_handoff_context',
    'add_to_shared_memory',
    'create_research_handoff',
    'COLLAB_TOOLS',
    # Audit
    'log_event',
    'log_session_start',
    'log_session_end',
    'log_security_event',
    'log_error',
    'get_session_stats',
    'search_logs',
    'export_logs',
    'audit_tool',
    'audit_context',
    'AUDIT_TOOLS',
    # IDE Server (Phase 4)
    'start_ide_server',
    'get_extension_template',
    'IDEHandler',
    'JSONRPCServer',
    'IDE_SERVER_TOOLS',
]
