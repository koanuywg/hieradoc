from hieradoc.storage.base import BaseTreeStorage
from hieradoc.storage.sqlite import SQLiteTreeStorage

__all__ = ["BaseTreeStorage", "SQLiteTreeStorage"]

# Supabase is optional
try:
    from hieradoc.storage.supabase import SupabaseTreeStorage
    __all__.append("SupabaseTreeStorage")
except ImportError:
    pass
