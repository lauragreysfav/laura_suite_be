from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Tracker(Base):
    __tablename__ = "trackers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    query = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrackerJob(Base):
    __tablename__ = "tracker_jobs"

    id = Column(Integer, primary_key=True, index=True)
    tracker_id = Column(Integer, ForeignKey("trackers.id"), nullable=False)
    status = Column(String(50), default="pending")
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class TrackedRelease(Base):
    __tablename__ = "tracked_releases"

    id = Column(Integer, primary_key=True, index=True)
    tracker_id = Column(Integer, ForeignKey("trackers.id"), nullable=False)
    title = Column(String(500), nullable=False)
    info_hash = Column(String(64), unique=True, nullable=False)
    magnet = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)
    quality = Column(String(50), nullable=True)
    seeders = Column(Integer, default=0)
    leechers = Column(Integer, default=0)
    released_at = Column(DateTime(timezone=True), nullable=True)
    downloaded = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False)
    type = Column(String(50), default="general")
    status = Column(String(50), default="pending")
    progress = Column(Integer, default=0)
    result_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("search_jobs.id"), nullable=False)
    title = Column(String(500), nullable=False)
    info_hash = Column(String(64), nullable=False)
    magnet = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    indexer = Column(String(255), nullable=True)
    size = Column(String(50), nullable=True)
    quality = Column(String(50), nullable=True)
    seeders = Column(Integer, default=0)
    leechers = Column(Integer, default=0)
    scene_id = Column(Integer, nullable=True)
    relevance = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, nullable=False)
    resume_time = Column(Float, default=0.0)
    play_count = Column(Integer, default=0)
    play_duration = Column(Float, default=0.0)
    last_played_at = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailConfig(Base):
    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String(255), default="smtp.gmail.com")
    port = Column(Integer, default=587)
    user = Column(String(255), default="")
    password = Column(String(255), default="")
    from_addr = Column(String(255), default="")
    enabled = Column(Boolean, default=False)
    notify_on_job_complete = Column(Boolean, default=True)
    notify_on_tracker_find = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StashDBPerformerCache(Base):
    __tablename__ = "stashdb_cache_performers"
    id = Column(Integer, primary_key=True)
    stashdb_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    aliases = Column(Text)
    image_url = Column(Text)
    scene_count = Column(Integer, default=0)
    career_years = Column(String(100))
    raw_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StashDBStudioCache(Base):
    __tablename__ = "stashdb_cache_studios"
    id = Column(Integer, primary_key=True)
    stashdb_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    image_url = Column(Text)
    scene_count = Column(Integer, default=0)
    parent_studio = Column(String(255))
    raw_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LibraryBulkJob(Base):
    __tablename__ = "library_bulk_jobs"
    id = Column(Integer, primary_key=True)
    performer_or_studio = Column(String(255), nullable=False)
    query_type = Column(String(50), nullable=False)
    status = Column(String(50), default="running")
    total_found = Column(Integer, default=0)
    sent_to_torbox = Column(Integer, default=0)
    error = Column(Text)


class LibraryTorrent(Base):
    __tablename__ = "library_torrents"
    id = Column(Integer, primary_key=True)
    info_hash = Column(String(64), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    performer_name = Column(String(255))
    studio_name = Column(String(255))
    quality = Column(String(50))
    size = Column(String(50))
    seeders = Column(Integer, default=0)
    source = Column(String(255))
    magnet = Column(Text)
    torrent_url = Column(Text)
    is_megapack = Column(Boolean, default=False)
    is_cached_torbox = Column(Boolean, default=False)
    is_local_stash = Column(Boolean, default=False)
    local_stash_path = Column(Text)
    torbox_id = Column(String(255))
    added_to_torbox_at = Column(DateTime(timezone=True))


class LibraryTorrentPreview(Base):
    __tablename__ = "library_torrent_previews"
    id = Column(Integer, primary_key=True)
    torrent_id = Column(Integer, ForeignKey("library_torrents.id"), nullable=False)
    image_url = Column(Text, nullable=False)


class LibraryAction(Base):
    __tablename__ = "library_actions"
    id = Column(Integer, primary_key=True)
    torrent_id = Column(Integer, ForeignKey("library_torrents.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # sent, dl, viewed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
