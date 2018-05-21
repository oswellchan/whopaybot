CREATE TABLE users (
	id INTEGER PRIMARY KEY,
	first_name TEXT,
	last_name TEXT,
	username TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE bills (
	id CHAR(16) PRIMARY KEY,
	title VARCHAR(255) NOT NULL,
	owner_id INTEGER REFERENCES users(id),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	completed_at TIMESTAMP WITH TIME ZONE,
	closed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE sessions (
	chat_id INTEGER,
	user_id INTEGER NOT NULL,
	action_type INTEGER,
	action_id INTEGER,
	subaction_id INTEGER,
	data TEXT,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE bill_taxes (
	id SERIAL PRIMARY KEY,
	bill_id CHAR(16) REFERENCES bills(id),
	title VARCHAR(255) NOT NULL,
	amount REAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE items (
	id SERIAL PRIMARY KEY,
	bill_id CHAR(16) REFERENCES bills(id),
	name TEXT NOT NULL,
	price REAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE bill_shares (
	id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES users(id),
	bill_id CHAR(16) REFERENCES bills(id),
	item_id INTEGER REFERENCES items(id),
	is_deleted BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (user_id, bill_id, item_id)
);

CREATE TABLE debts (
	id SERIAL PRIMARY KEY,
	debtor_id INTEGER REFERENCES users(id),
	creditor_id INTEGER REFERENCES users(id),
	bill_id CHAR(16) REFERENCES bills(id),
	original_amt REAL NOT NULL,
	is_deleted BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (debtor_id, creditor_id, bill_id)
);

CREATE TABLE payments (
	id SERIAL PRIMARY KEY,
	type SMALLINT NOT NULL,
	debt_id INTEGER REFERENCES debts(id),
	amount REAL NOT NULL,
	comments VARCHAR(255),
	is_deleted BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	confirmed_at TIMESTAMP WITH TIME ZONE
);