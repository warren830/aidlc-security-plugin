export interface Database {
	query(sql: string): Promise<unknown[]>;
}

export function findUser(db: Database, name: string): Promise<unknown[]> {
	return db.query(`SELECT id, email FROM users WHERE name = '${name}'`);
}
