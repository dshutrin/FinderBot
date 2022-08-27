from peewee import *


db = SqliteDatabase('data.db')


class User(Model):
	class Meta:
		database = db
		db_table = 'Users'

	vk_id = IntegerField()
	mode = CharField(max_length=100)


class Photo(Model):
	class Meta:
		database = db
		db_table = 'Photos'

	photo = BlobField()
	photo_link = TextField()
	post_link = TextField()


if __name__ == '__main__':
	db.create_tables([User, Photo])
