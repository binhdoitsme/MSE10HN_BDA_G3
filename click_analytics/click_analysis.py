import os
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json, struct, to_json, when
from pyspark.sql.types import StringType, StructField, StructType, TimestampType


db_url = os.getenv("DB_URL", "")


def save_to_database(df: DataFrame, epoch_id):
    df.printSchema()
    return (
        df.write.format("jdbc")
        .mode("append")
        .option("driver", "org.postgresql.Driver")
        .option("url", db_url)
        .option("dbtable", "clicks")
        .save()
    )


def main():
    spark = SparkSession.Builder().appName("ClickAnalytics").getOrCreate()
    spark.sparkContext.setLogLevel("INFO")
    schema = StructType(
        [
            StructField("session_id", StringType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("product_id", StringType(), True),
            StructField("user_agent", StringType(), True),
        ]
    )
    df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "stream_analytics")
        .load()
        .withColumn("json", from_json(col("value").cast("string"), schema))
    )
    df.printSchema()
    df = df.select(
        col("json.session_id").alias("session_id"),
        col("json.timestamp").alias("timestamp"),
        col("json.product_id").alias("product_id"),
        when(df["json.user_agent"].rlike("iPhone|iPad|iPod|iOS"), "iOS")
        .when(df["json.user_agent"].rlike("Android"), "Android")
        .when(df["json.user_agent"].rlike("Windows"), "Windows")
        .when(df["json.user_agent"].rlike("Macintosh|Mac OS X"), "Mac OS X")
        .otherwise("Other")
        .alias("device"),
    )
    df.printSchema()

    s1 = (
        df.select(to_json(struct([df[x] for x in df.columns])).alias("value"))
        .writeStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("topic", "live_report")
        .option("checkpointLocation", "/tmp/spark/checkpoint")
        .start()
    )
    s2 = df.writeStream.foreachBatch(save_to_database).start()
    # print(s1)
    # print(s2)
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
