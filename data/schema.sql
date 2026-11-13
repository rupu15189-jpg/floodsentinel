-- 由 backend/tools/dump_schema.py 自动生成，请勿手改
-- 与 backend/app/models.py 一一对应

CREATE TABLE report (
	id VARCHAR(32) NOT NULL, 
	alert_ids JSON NOT NULL, 
	content_md TEXT NOT NULL, 
	citations JSON NOT NULL, 
	model VARCHAR(64) NOT NULL, 
	fallback BOOLEAN NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE scenario (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	duration_min INTEGER NOT NULL, 
	seed INTEGER NOT NULL, 
	injections JSON NOT NULL, 
	expected JSON NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE station (
	id VARCHAR(32) NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	type VARCHAR(16) NOT NULL, 
	lng FLOAT NOT NULL, 
	lat FLOAT NOT NULL, 
	basin_id VARCHAR(32) NOT NULL, 
	warn_level FLOAT, 
	guarantee_level FLOAT, 
	history_max FLOAT, 
	status VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_station_type ON station (type);
CREATE UNIQUE INDEX ix_station_code ON station (code);
CREATE INDEX ix_station_basin_id ON station (basin_id);

CREATE TABLE alert (
	id VARCHAR(32) NOT NULL, 
	station_id VARCHAR(32) NOT NULL, 
	level VARCHAR(8) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	evidence JSON NOT NULL, 
	dedup_key VARCHAR(64) NOT NULL, 
	triggered_at DATETIME NOT NULL, 
	confirmed_by VARCHAR(32), 
	confirmed_at DATETIME, 
	closed_at DATETIME, 
	close_reason VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(station_id) REFERENCES station (id)
);
CREATE INDEX ix_alert_level ON alert (level);
CREATE INDEX ix_alert_status ON alert (status);
CREATE UNIQUE INDEX ix_alert_dedup_key ON alert (dedup_key);
CREATE INDEX ix_alert_station_id ON alert (station_id);
CREATE INDEX ix_alert_triggered_at ON alert (triggered_at);

CREATE TABLE observation (
	id INTEGER NOT NULL, 
	station_id VARCHAR(32) NOT NULL, 
	ts DATETIME NOT NULL, 
	metric VARCHAR(32) NOT NULL, 
	value FLOAT NOT NULL, 
	unit VARCHAR(8) NOT NULL, 
	quality VARCHAR(8) NOT NULL, 
	source VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(station_id) REFERENCES station (id)
);
CREATE INDEX ix_obs_station_ts ON observation (station_id, ts);
CREATE INDEX ix_observation_station_id ON observation (station_id);
CREATE INDEX ix_observation_ts ON observation (ts);
CREATE INDEX ix_obs_metric_ts ON observation (metric, ts);
