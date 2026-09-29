"""
Build questions.js for the DVA-C02 quiz app.

Usage:  python build_questions.py
Reads every *.txt file in this folder (format: "Q<n> ... Options: A. ... Correct Answer: X. ..."),
removes duplicate questions, attaches explanations/topics, appends the extra
DVA-C02 questions defined below, and writes questions.js.
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Explanations for the questions in the .txt file (keyed by question number;
# a repeated number gets a "b" suffix, e.g. the second Q35 is "35b").
# ---------------------------------------------------------------------------
EXPLANATIONS = {
    "1": "Each shard supports 1 MB/s or 1,000 records/s of writes. When the stream itself can't keep up, add capacity by increasing the shard count (UpdateShardCount / resharding). KPL and PutRecords improve producer efficiency but don't raise the stream's limits.",
    "2": "AWS SAM can deploy API Gateway REST APIs from an OpenAPI/Swagger definition either inline in the template or referenced from a separate file (DefinitionUri / DefinitionBody with AWS::Include).",
    "3": "CloudWatch Logs is the central, encrypted, durable store for application logs (use the CloudWatch agent on EC2). VPC Flow Logs capture network traffic, CloudTrail captures API calls.",
    "4": "EBS encryption encrypts data at rest AND in transit between the instance and the volume. OS-level (file system) encryption also protects data before it leaves the instance.",
    "5": "Short, intermittent throttling bursts are best handled with retries using exponential backoff (the AWS SDKs do this automatically). Changing capacity is not needed for 15-second spikes.",
    "6": "The 'Transform: AWS::Serverless-2016-10-31' section tells CloudFormation to process the template with the SAM macro so AWS::Serverless::* resources are expanded.",
    "7": "EC2/on-prem in-place order: ApplicationStop → DownloadBundle → BeforeInstall → Install → AfterInstall → ApplicationStart → ValidateService.",
    "8": "Best practice: never create/keep root access keys, and prefer IAM roles (temporary credentials) over long-term access keys.",
    "9": "portMappings are part of the container definition inside the ECS task definition.",
    "10": "Multi-container Docker on Elastic Beanstalk (ECS-based platform) uses a Dockerrun.aws.json v2 file, which is essentially an ECS task definition.",
    "11": "An EC2 instance profile delivers an IAM role's temporary, auto-rotated credentials to the instance — no keys to store or rotate.",
    "12": "Exponential backoff smooths retries, and raising provisioned capacity (or using on-demand) removes the underlying throughput shortage.",
    "13": "AWS X-Ray collects traces and builds a service map; it supports cross-account tracing (e.g. via CloudWatch cross-account observability).",
    "14": "Package dependencies with your function code (ZIP, or better today a Lambda layer / container image). Lambda can't load libraries at runtime from S3 or modify the managed runtime.",
    "15": "RequestLimitExceeded is API throttling. The client should retry with exponential backoff and jitter and reduce request rate.",
    "16": "Use PutMetricData to publish custom metrics, and grant permission via an IAM role on the instance (never hard-coded credentials).",
    "17": "CodePipeline has a built-in Manual Approval action that pauses the pipeline in a stage until someone approves/rejects it.",
    "18": "A bucket policy with Deny on s3:PutObject when x-amz-server-side-encryption header is missing enforces encryption on upload. (Today S3 also encrypts all new objects by default with SSE-S3.)",
    "19": "X-Ray traces requests across distributed components and shows latency per segment/subsegment and errors, pinpointing the root cause.",
    "20": "Growing IteratorAge means consumers fall behind. More shards = more parallel Lambda invocations; more memory = more CPU = faster processing per batch.",
    "21": "Use a bucket policy that Denies any request where aws:SecureTransport is false, forcing HTTPS (TLS) for all traffic.",
    "22": "A GSI with only the needed projected attributes lets queries read smaller items, consuming fewer RCUs and returning faster.",
    "23": "Rolling deployments update batches of instances, keeping part of the fleet serving traffic without the cost/time of a full new fleet. (Note: many practice sets argue Immutable for maximum availability — know the trade-offs of each policy.)",
    "24": "S3 invokes Lambda asynchronously. On failure/timeout Lambda retries twice (3 attempts total); without a DLQ or on-failure destination, the event is then discarded.",
    "25": "Kinesis Data Streams is built for real-time ingestion of high-volume streaming data from many producers; KCL consumers process it in real time.",
    "26": "Run the X-Ray daemon (e.g. amazon/aws-xray-daemon image, commonly as a sidecar) and instrument the code with the X-Ray SDK to get traces and a service map.",
    "27": "The browser blocks JavaScript requests to a different origin (the other bucket's endpoint) unless that bucket returns CORS headers. Configure CORS on the bucket serving the images.",
    "28": "Partitioning by date creates a hot partition. Write sharding (adding a random/calculated suffix to the partition key) spreads writes evenly across partitions with no extra cost.",
    "32": "User pools handle sign-up/sign-in and self-service password changes; identity pools exchange tokens for temporary AWS credentials to access AWS services.",
    "33": "Cross-account access: the Account B role needs sts:AssumeRole permission on the AccessPII role, and the application must call AssumeRole to get temporary credentials.",
    "34": "CodeDeploy uses appspec.yml (or .json) to describe the deployment; for Lambda it specifies the function, alias and versions to shift traffic between.",
    "35": "An ALB replaces the source IP with its own. The original client IP is in the X-Forwarded-For header (which can contain a list if there are multiple proxies).",
    "35b": "Ship logs off the instance with the CloudWatch agent so they're centralized and retained, then remove local copies to free disk space.",
    "36": "API Gateway stages (e.g. v1, v2, test) give each version its own endpoint; stage variables can point to different Lambda aliases/backends.",
    "37": "You cannot encrypt an existing unencrypted RDS instance in place. Snapshot → copy the snapshot with encryption enabled → restore a new instance from the encrypted snapshot.",
    "38": "DynamoDB Accelerator (DAX) is an in-memory cache for DynamoDB delivering microsecond reads, and is API-compatible so it needs minimal code changes.",
    "39": "Writing to the database and then invalidating (deleting) the cache entry ensures the next read loads fresh data, keeping price info consistent.",
    "40": "Store the object key, and generate a short-lived presigned URL each time it's needed. Storing a presigned URL doesn't work long-term because it expires.",
    "41": "Kinesis Data Streams supports server-side encryption at rest using AWS KMS keys.",
    "42": "put-metric-alarm only creates an alarm. Data must be published with put-metric-data (PutMetricData) for the metric to appear.",
    "43": "Least privilege: grant only the specific actions needed — codecommit:CreateBranch and codecommit:DeleteBranch.",
    "44": "In a non-proxy (custom) integration, a Velocity (VTL) mapping template transforms the request (query strings → JSON payload) for Lambda.",
    "45": "API Gateway canary release deployments send a configurable percentage of stage traffic to the new deployment (canarySettings).",
    "49": "KMS keys (customer managed) support automatic key rotation — yearly by default (configurable) — with no code changes.",
    "50": "Usage plans + API keys let you set per-customer throttling and quota limits to match each SLA.",
    "51": "The browser call goes to API Gateway, so CORS must be enabled on the API Gateway method (and the OPTIONS preflight), returning Access-Control-Allow-Origin.",
    "52": "Lambda's max timeout is 15 minutes and can't be increased. Use SQS + an Auto Scaling group of EC2 workers for long-running, scalable processing.",
    "53": "On-premises servers can't use instance roles; configure credentials (e.g. an IAM user or IAM Roles Anywhere) via the SDK credential chain — never in source code.",
    "54": "Running the CodeBuild agent locally lets developers build/test before pushing, at no CodeBuild cost.",
    "55": "Use IAM fine-grained access control with the dynamodb:LeadingKeys condition so each user can only access items whose partition key matches their identity.",
    "58": "API Gateway doesn't have a 'SOAP API' type. Create a REST API and use mapping templates to transform JSON into the XML SOAP request.",
    "59": "AWS Step Functions orchestrates Lambda functions as a state machine with built-in retries, error handling and visual workflow.",
    "60": "IAM roles for tasks are set per task definition (taskRoleArn), giving each service its own least-privilege permissions even when sharing instances.",
    "61": "Metric filters aren't retroactive — they only generate data for log events ingested after the filter is created.",
    "62": "ChangeMessageVisibility extends the visibility timeout of an in-flight message so other consumers don't receive it while processing continues.",
    "63": "ElastiCache (Redis/Memcached) provides an in-memory cache for repeated read queries, reducing database load and latency.",
    "64": "Change sets preview how proposed changes will affect running resources (add, modify, replace) before you execute the update.",
    "65": "S3 PutObject requires the Content-Length header for a standard (non-chunked) upload; missing it returns 400 Bad Request (MissingContentLength).",
    "66": "Bake the application into a custom AMI to cut boot time, then reference the new AMI in the launch template in the CloudFormation template.",
    "67": "Lambda is stateless; store session state externally in a fast, scalable store like DynamoDB (or ElastiCache).",
    "68": "A LAMP stack needs servers (EC2 for Linux/Apache/PHP) and a MySQL-compatible database (Aurora MySQL / RDS).",
    "69": "ThrottlingException means you're exceeding API rate limits. First implement retries with exponential backoff.",
    "70": "Standard queues offer at-least-once delivery. FIFO queues with content-based or explicit deduplication give exactly-once processing within the 5-minute dedup interval. (A standard queue can't be converted to FIFO — create a new one.)",
    "77": "Conditional writes (ConditionExpression, e.g. optimistic locking with a version attribute) only succeed if the item is in the expected state, preventing lost updates.",
    "78": "AWS::Lambda::Function code can be inline (ZipFile, small functions) or a ZIP in S3 (S3Bucket/S3Key). It can also be a container image in ECR.",
    "79": "On EC2 the SDK sends segments to the X-Ray daemon (which must be installed/running), and the instance role needs xray:PutTraceSegments and xray:PutTelemetryRecords (AWSXRayDaemonWriteAccess).",
    "85": "The AWS CLI authenticates with access keys (or SSO/roles), never an IAM console password or an SSH key.",
    "86": "Both DAX and ElastiCache cache hot data in memory, serving repeated reads of a small data set with lower latency.",
    "87": "To use a key the company controls, choose a KMS customer managed key when creating the table. DynamoDB encryption at rest is transparent — no code changes.",
    "88": "The execution role needs s3:ListAllMyBuckets (ListBuckets) and dynamodb:PutItem. AWSLambdaBasicExecutionRole only grants CloudWatch Logs permissions.",
    "89": "The AWS SDK (boto3) has built-in automatic retries with exponential backoff.",
    "90": "The context object contains aws_request_id (awsRequestId). Writing to stdout/console sends logs to CloudWatch Logs automatically.",
    "91": "Immutable deployments launch a full new set of instances in a temporary ASG, keeping full capacity; if it fails, just terminate the new instances.",
    "92": "API Gateway provides a single front door to many backend services with auth, throttling, and versioning.",
    "93": "Store large or sensitive values in Systems Manager Parameter Store (or Secrets Manager) and reference them in buildspec env/parameter-store.",
    "94": "API Gateway in front of the backend with server-side (stage/account) throttling limits caps total requests for all clients without code changes. Per-client throttling would need API keys/usage plans for each new client.",
    "102": "CloudFront Functions are lightweight edge functions that can read the CloudFront-Viewer-Country header and return a redirect — least operational effort.",
    "103": "Lambda writes its logs (errors, stack traces) to CloudWatch Logs — the place to find function errors.",
    "104": "X-Forwarded-For carries the original client IP address through the load balancer.",
    "105": "Cognito IDENTITY pools federate SAML and social identity providers and issue temporary AWS credentials for services like DynamoDB. User pools alone only issue JWTs (they can federate SAML/social but can't give AWS credentials by themselves). NOTE: your source file listed C (user pools); B is the widely accepted answer.",
    "106": "DynamoDB scales automatically and stores data durably long-term; DAX caches frequently read carts for fast retrieval. Fully serverless.",
    "107": "RDS read replicas offload read traffic; point read queries at the replica's endpoint via a separate connection string.",
    "108": "Secrets Manager stores credentials encrypted and supports automatic rotation for RDS databases.",
    "109": "Least privilege: CloudFormation service role with only needed S3 permissions, and a bucket policy scoped to the specific account IDs (not '*').",
    "110": "Presigned URLs give time-limited access (up to 7 days with SigV4 using IAM user credentials) without creating IAM users or making the object public.",
    "111": "S3 supports 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD requests per second PER PREFIX. Spreading keys across prefixes scales throughput.",
    "112": "Lambda in private subnets has no internet access. An interface VPC endpoint (PrivateLink) for SSM lets it reach Systems Manager privately. Gateway endpoints exist only for S3 and DynamoDB.",
    "113": "Encrypting sensitive fields at the edge (Lambda@Edge or CloudFront field-level encryption) with a KMS key protects data throughout its lifecycle in AWS.",
    "114": "Invocation works but the DynamoDB write fails — the execution role is missing dynamodb:PutItem (or similar) permissions.",
    "115": "CodeCommit is AWS's managed Git source repository (note: CodeCommit closed to new customers in 2024; exam still covers it as the source store).",
    "116": "An SQS delay queue (DelaySeconds up to 900s) hides messages for 10 minutes; Lambda then processes each message once.",
    "117": "DynamoDB Streams capture item changes without consuming table read capacity; a Lambda trigger can publish notifications via SNS.",
    "118": "Viewer Protocol Policy = Redirect HTTP to HTTPS encrypts viewer→CloudFront; Origin Protocol Policy = Match Viewer (or HTTPS Only) encrypts CloudFront→ALB.",
    "119": "Lambda's /tmp ephemeral storage (512 MB default, configurable up to 10 GB) is ideal for temporary files used only during the invocation.",
    "120": "Cognito identity pools support unauthenticated (guest) identities mapped to a limited IAM role with temporary credentials.",
    "121": "Blue/green (swap environment URLs) and Immutable (new instances in a temporary ASG) both replace the old instances, which are terminated after deployment.",
}

# Answers in the source file that we override (id -> list of correct letters)
ANSWER_OVERRIDES = {
    "105": ["B"],
}

# ---------------------------------------------------------------------------
# Extra important DVA-C02 questions
# ---------------------------------------------------------------------------
EXTRA = [
    # ---------------- Lambda ----------------
    {
        "q": "A Lambda function experiences high latency on the first invocations after a period of inactivity due to cold starts. The function is behind an API Gateway API with predictable traffic during business hours. What is the MOST effective way to eliminate cold-start latency?",
        "options": ["Increase the function timeout.", "Configure provisioned concurrency on a function alias.", "Configure reserved concurrency for the function.", "Increase the function's ephemeral storage."],
        "answer": ["B"],
        "explanation": "Provisioned concurrency keeps a set number of execution environments initialized and ready. Reserved concurrency only caps/guarantees a concurrency limit, it does not pre-warm environments. Provisioned concurrency must target a version or alias (not $LATEST).",
    },
    {
        "q": "A Lambda function processes orders and must never consume all of the account's concurrency, while also always being able to scale to at least 100 concurrent executions. What should the developer configure?",
        "options": ["Provisioned concurrency of 100", "Reserved concurrency of 100", "A Lambda layer", "An SQS dead-letter queue"],
        "answer": ["B"],
        "explanation": "Reserved concurrency both guarantees that amount of concurrency for the function and acts as the maximum it can use, protecting other functions in the account.",
    },
    {
        "q": "Several Lambda functions share the same custom libraries. The developer wants to manage these dependencies separately and reduce deployment package size. What should the developer use?",
        "options": ["Lambda environment variables", "Lambda layers", "Lambda extensions", "Lambda aliases"],
        "answer": ["B"],
        "explanation": "Lambda layers package libraries/runtimes/config separately and can be shared by many functions (up to 5 layers per function; 250 MB unzipped total).",
    },
    {
        "q": "A developer wants to gradually shift 10% of traffic to a new Lambda version, then shift the rest if no errors occur. Which features should be used? (Select TWO.)",
        "options": ["Lambda alias with weighted routing", "Lambda layers", "AWS CodeDeploy with a canary deployment configuration (e.g. LambdaCanary10Percent5Minutes)", "Reserved concurrency", "Lambda environment variables"],
        "answer": ["A", "C"],
        "explanation": "Aliases can split traffic between two versions (routing config). CodeDeploy (or SAM's DeploymentPreference/AutoPublishAlias) automates canary/linear shifting with CloudWatch alarm rollback.",
    },
    {
        "q": "An asynchronously invoked Lambda function occasionally fails. The developer wants failed events, along with details of the failure and the response, to be sent to an SQS queue. What is the BEST solution?",
        "options": ["Configure a dead-letter queue on the function", "Configure an on-failure destination for asynchronous invocation", "Wrap the handler in try/catch and send to SQS manually", "Enable X-Ray active tracing"],
        "answer": ["B"],
        "explanation": "Lambda Destinations (on-success/on-failure) for async invocations send the event plus invocation record details (response, error). A DLQ only receives the original event payload. Destinations are the recommended newer option.",
    },
    {
        "q": "A Lambda function stores a database connection string in an environment variable. Company policy requires that sensitive environment variables be encrypted with a company-controlled key and not visible in the console. What should the developer do?",
        "options": ["Nothing; environment variables are always encrypted with a customer managed key", "Use encryption helpers to encrypt the value client-side with a KMS customer managed key and decrypt it in the function code", "Store the value in the function code", "Store the value in a Lambda layer"],
        "answer": ["B"],
        "explanation": "Environment variables are encrypted at rest with an AWS managed key by default. For in-transit/console protection, use encryption helpers with a customer managed KMS key and call kms:Decrypt in code (or better, use Secrets Manager/Parameter Store).",
    },
    {
        "q": "Where should a developer initialize SDK clients and database connections in a Lambda function to improve performance across invocations?",
        "options": ["Inside the handler function", "Outside the handler function (in the initialization code)", "In a Lambda layer's environment variables", "In the /tmp directory"],
        "answer": ["B"],
        "explanation": "Code outside the handler runs once per execution environment and is reused by subsequent (warm) invocations — ideal for SDK clients and DB connections.",
    },
    {
        "q": "A Lambda function in a VPC private subnet needs to call a public third-party API on the internet. What is required?",
        "options": ["An internet gateway attached to the Lambda function", "A NAT gateway in a public subnet and a route from the private subnet to it", "A public IP address on the Lambda function", "A gateway VPC endpoint"],
        "answer": ["B"],
        "explanation": "Lambda ENIs in a VPC never get public IPs. Internet access from private subnets requires a NAT gateway (in a public subnet with an IGW route).",
    },
    {
        "q": "What is the maximum execution timeout for an AWS Lambda function?",
        "options": ["5 minutes", "15 minutes", "30 minutes", "60 minutes"],
        "answer": ["B"],
        "explanation": "Lambda functions can run for at most 900 seconds (15 minutes). Longer workloads belong on ECS/Fargate, Step Functions, Batch, or EC2.",
    },
    {
        "q": "A Lambda function is invoked through API Gateway (synchronous invocation) and returns an error. What happens to the request?",
        "options": ["Lambda retries it twice automatically", "The error is returned to the caller; the caller is responsible for retries", "It is sent to the function's dead-letter queue", "It is retried until the event expires"],
        "answer": ["B"],
        "explanation": "Synchronous invocations are not retried by Lambda — the error goes back to the client. Async invocations get 2 retries; stream/queue event source mappings retry based on the source.",
    },
    {
        "q": "A developer is invoking a Lambda function with the AWS CLI and wants it to be invoked asynchronously. Which parameter should be used?",
        "options": ["--invocation-type RequestResponse", "--invocation-type Event", "--invocation-type DryRun", "--log-type Tail"],
        "answer": ["B"],
        "explanation": "InvocationType=Event queues the event for asynchronous invocation. RequestResponse is synchronous (default). DryRun only validates permissions.",
    },
    # ---------------- DynamoDB ----------------
    {
        "q": "An application reads items of 6 KB each from a DynamoDB table at 10 strongly consistent reads per second. How many RCUs are required?",
        "options": ["10", "15", "20", "60"],
        "answer": ["C"],
        "explanation": "1 RCU = one strongly consistent read/sec of up to 4 KB. 6 KB rounds up to 8 KB = 2 RCUs per read × 10 = 20 RCUs. (Eventually consistent would be half: 10.)",
    },
    {
        "q": "An application writes 5 items per second to a DynamoDB table. Each item is 2.5 KB. How many WCUs are required?",
        "options": ["5", "10", "13", "15"],
        "answer": ["D"],
        "explanation": "1 WCU = one write/sec of up to 1 KB. 2.5 KB rounds up to 3 KB = 3 WCUs per write × 5 = 15 WCUs. (Transactional writes cost double.)",
    },
    {
        "q": "A developer needs a new query pattern on an existing DynamoDB table using a different partition key. What should be created?",
        "options": ["Local secondary index (LSI)", "Global secondary index (GSI)", "A DynamoDB stream", "A new sort key on the base table"],
        "answer": ["B"],
        "explanation": "GSIs can have a different partition and sort key and can be added any time. LSIs share the base table's partition key and can only be created at table creation.",
    },
    {
        "q": "Which DynamoDB operation is the MOST efficient way to retrieve all orders for a specific customer ID, where customer ID is the partition key?",
        "options": ["Scan with a FilterExpression", "Query with a KeyConditionExpression", "GetItem", "BatchWriteItem"],
        "answer": ["B"],
        "explanation": "Query reads only items with the given partition key. Scan reads the whole table and filters afterward (consuming RCUs for everything read). GetItem needs the full primary key.",
    },
    {
        "q": "A Scan on a large DynamoDB table takes too long. How can the developer speed it up?",
        "options": ["Use a parallel scan with the Segment and TotalSegments parameters", "Use a ProjectionExpression", "Use strongly consistent reads", "Decrease the page size to 1"],
        "answer": ["A"],
        "explanation": "Parallel scans split the table into segments that multiple workers scan concurrently. ProjectionExpression reduces returned data but not RCUs consumed.",
    },
    {
        "q": "A developer wants session items in DynamoDB to be deleted automatically 24 hours after creation at no extra cost. What should be used?",
        "options": ["A scheduled Lambda function that deletes old items", "DynamoDB Time to Live (TTL) with an epoch-timestamp attribute", "DynamoDB Streams", "A GSI on the creation date"],
        "answer": ["B"],
        "explanation": "TTL deletes expired items automatically (usually within a few days of expiry) without consuming WCUs. The attribute must be a Number in Unix epoch seconds.",
    },
    {
        "q": "A developer must update two items in different DynamoDB tables so that either both updates succeed or neither does. What should be used?",
        "options": ["BatchWriteItem", "TransactWriteItems", "Conditional writes on each item", "UpdateItem with ReturnValues"],
        "answer": ["B"],
        "explanation": "TransactWriteItems gives all-or-nothing ACID writes across up to 100 items in one or more tables. BatchWriteItem is not atomic — individual items can fail.",
    },
    {
        "q": "A BatchGetItem call returns successfully but some keys are missing from the result. What should the developer do?",
        "options": ["Increase the table's RCUs immediately", "Retry the items in UnprocessedKeys using exponential backoff", "Switch to Scan", "Ignore them; they don't exist"],
        "answer": ["B"],
        "explanation": "Batch operations can partially succeed (e.g. throttling or 16 MB limit). Unprocessed items are returned in UnprocessedKeys/UnprocessedItems and should be retried with backoff.",
    },
    {
        "q": "A DynamoDB table uses a 'version' attribute. Before updating, the application checks that the version equals the value it read. What is this technique called?",
        "options": ["Pessimistic locking", "Optimistic locking with conditional writes", "Write sharding", "Atomic counters"],
        "answer": ["B"],
        "explanation": "Optimistic locking uses a ConditionExpression on a version number; if another writer changed it, ConditionalCheckFailedException is thrown and the client re-reads and retries.",
    },
    {
        "q": "Which DynamoDB Streams view type should be used if the consumer needs both the item before and after it was modified?",
        "options": ["KEYS_ONLY", "NEW_IMAGE", "OLD_IMAGE", "NEW_AND_OLD_IMAGES"],
        "answer": ["D"],
        "explanation": "NEW_AND_OLD_IMAGES includes both versions of the item. Stream records are retained for 24 hours.",
    },
    # ---------------- S3 ----------------
    {
        "q": "An application uploads files larger than 5 GB to Amazon S3. Which approach must be used?",
        "options": ["A single PutObject request", "Multipart upload", "S3 Transfer Acceleration only", "S3 Batch Operations"],
        "answer": ["B"],
        "explanation": "A single PUT supports objects up to 5 GB. Multipart upload is required above 5 GB (max object 5 TB) and recommended above 100 MB.",
    },
    {
        "q": "An application using SSE-KMS on S3 starts receiving ThrottlingException errors during heavy uploads/downloads. What is the MOST likely cause?",
        "options": ["The S3 prefix request limit", "KMS API request quota for GenerateDataKey/Decrypt is being exceeded", "The bucket is out of storage", "The IAM role session expired"],
        "answer": ["B"],
        "explanation": "Every SSE-KMS PUT calls GenerateDataKey and every GET calls Decrypt, counting against KMS per-second quotas. Mitigate with S3 Bucket Keys, quota increases, or SSE-S3.",
    },
    {
        "q": "A company must encrypt S3 objects with its own keys that it manages outside AWS, and AWS must not store the keys. Which option should be used?",
        "options": ["SSE-S3", "SSE-KMS with a customer managed key", "SSE-C", "DSSE-KMS"],
        "answer": ["C"],
        "explanation": "With SSE-C you provide the key on every request (over HTTPS); S3 uses it to encrypt/decrypt and then discards it. With SSE-KMS the keys live in KMS.",
    },
    {
        "q": "A developer wants a Lambda function to run every time an image is uploaded to an S3 bucket. What should be configured?",
        "options": ["An S3 event notification for s3:ObjectCreated:* targeting the Lambda function", "An S3 Lifecycle rule", "S3 Replication", "An S3 Inventory report"],
        "answer": ["A"],
        "explanation": "S3 event notifications can invoke Lambda, SQS, SNS (or send to EventBridge). S3 needs a resource-based permission to invoke the function.",
    },
    {
        "q": "Users upload files directly from a browser to a private S3 bucket without the application proxying the data and without AWS credentials in the browser. What should the backend provide?",
        "options": ["The bucket's access keys", "A presigned URL for PutObject", "A public-write bucket policy", "An S3 access point with public access"],
        "answer": ["B"],
        "explanation": "A presigned PUT URL (or presigned POST) generated by the backend lets clients upload directly for a limited time using the signer's permissions.",
    },
    {
        "q": "A company wants a CloudFront distribution to be the ONLY way users can access objects in a private S3 bucket. What is the recommended solution?",
        "options": ["Make the bucket public", "Use Origin Access Control (OAC) and a bucket policy allowing only the CloudFront distribution", "Use S3 website hosting endpoint", "Use signed cookies only"],
        "answer": ["B"],
        "explanation": "OAC (successor to OAI) signs CloudFront requests to S3; the bucket policy allows only that distribution, blocking direct S3 access.",
    },
    # ---------------- SQS / SNS / Kinesis / EventBridge ----------------
    {
        "q": "An application polling an SQS queue receives many empty responses, which increases cost. What should the developer do?",
        "options": ["Use short polling", "Enable long polling by setting ReceiveMessageWaitTimeSeconds up to 20", "Decrease the visibility timeout", "Use a FIFO queue"],
        "answer": ["B"],
        "explanation": "Long polling waits up to 20 seconds for messages, reducing empty receives and API calls (cost).",
    },
    {
        "q": "Messages that repeatedly fail processing keep returning to an SQS queue. What should the developer configure to isolate them for analysis?",
        "options": ["A delay queue", "A dead-letter queue with a redrive policy (maxReceiveCount)", "Long polling", "Message timers"],
        "answer": ["B"],
        "explanation": "After maxReceiveCount receives, SQS moves the message to the DLQ. A FIFO queue's DLQ must also be FIFO.",
    },
    {
        "q": "An SQS FIFO queue must process orders for each customer in order, but orders for different customers in parallel. What should the developer set?",
        "options": ["MessageDeduplicationId to the customer ID", "MessageGroupId to the customer ID", "DelaySeconds per customer", "A separate queue per customer"],
        "answer": ["B"],
        "explanation": "Ordering is guaranteed within a message group. Different MessageGroupIds are processed in parallel.",
    },
    {
        "q": "An SQS message payload is 1 GB. How can the developer send it through SQS?",
        "options": ["Increase the SQS message size limit", "Use the SQS Extended Client Library to store the payload in S3 and send a reference", "Split it using FIFO groups", "Compress it into a message attribute"],
        "answer": ["B"],
        "explanation": "SQS messages are limited to 256 KB (newer quotas allow 1 MiB). The Extended Client Library stores large payloads in S3 and sends a pointer.",
    },
    {
        "q": "An order event must be processed independently by an inventory service, a shipping service, and an analytics service. Each service must receive every message even if another service is down. Which architecture is BEST?",
        "options": ["One SQS queue polled by all three services", "SNS topic fan-out to three SQS queues, one per service", "Kinesis Data Firehose to S3", "Three Lambda functions invoked in sequence"],
        "answer": ["B"],
        "explanation": "SNS + SQS fan-out delivers a copy to each queue; each service consumes at its own pace and messages persist if a consumer is down.",
    },
    {
        "q": "An SNS topic has several SQS subscribers. One subscriber should receive only messages where order_type = 'priority'. What should be used?",
        "options": ["A separate SNS topic", "An SNS subscription filter policy", "SQS message timers", "A Lambda authorizer"],
        "answer": ["B"],
        "explanation": "Subscription filter policies (on message attributes or body) let each subscriber receive only matching messages.",
    },
    {
        "q": "A Kinesis Data Stream has enough total shards, but one shard is throttled while others are idle. What is the MOST likely cause?",
        "options": ["The retention period is too short", "A poorly distributed partition key creates a hot shard", "Server-side encryption is enabled", "Enhanced fan-out is disabled"],
        "answer": ["B"],
        "explanation": "Records with the same partition key go to the same shard. Use a high-cardinality partition key to spread load evenly.",
    },
    {
        "q": "Five different consumer applications read from the same Kinesis Data Stream and are hitting the 2 MB/s per-shard read limit. What should the developer use?",
        "options": ["Kinesis enhanced fan-out", "More partition keys", "Longer retention period", "Kinesis Data Firehose"],
        "answer": ["A"],
        "explanation": "Enhanced fan-out gives each registered consumer its own 2 MB/s per shard via HTTP/2 push (SubscribeToShard).",
    },
    {
        "q": "A developer needs to deliver streaming data to Amazon S3 in near-real time with automatic batching, compression, and optional Lambda transformation, with no consumer code. Which service?",
        "options": ["Kinesis Data Streams", "Amazon Data Firehose (Kinesis Data Firehose)", "Amazon SQS", "Amazon MQ"],
        "answer": ["B"],
        "explanation": "Firehose is fully managed delivery to S3, Redshift, OpenSearch, Splunk, HTTP endpoints — near real time with buffering, no code needed.",
    },
    {
        "q": "A developer wants to run a Lambda function every day at 02:00 UTC. What is the simplest solution?",
        "options": ["An EC2 instance running cron", "An Amazon EventBridge Scheduler schedule (or scheduled rule) with a cron expression", "An SQS delay queue", "A Step Functions Wait state"],
        "answer": ["B"],
        "explanation": "EventBridge Scheduler / scheduled rules support cron and rate expressions to invoke targets like Lambda serverlessly.",
    },
    # ---------------- API Gateway ----------------
    {
        "q": "A Lambda function behind an API Gateway Lambda proxy integration returns data, but clients receive '502 Bad Gateway'. What is the MOST likely cause?",
        "options": ["The Lambda timeout is too high", "The function's response is not in the required proxy format (statusCode, headers, body as a string)", "CORS is not enabled", "The API key is missing"],
        "answer": ["B"],
        "explanation": "With proxy integration, Lambda must return JSON with statusCode, headers and a string body. Malformed responses produce 502. Timeouts produce 504.",
    },
    {
        "q": "An API Gateway REST API returns '504 Gateway Timeout' for long-running requests even though the Lambda function has a 5-minute timeout. Why?",
        "options": ["The Lambda concurrency limit was reached", "API Gateway's integration timeout (default 29 seconds) was exceeded", "The API is not deployed", "Caching is disabled"],
        "answer": ["B"],
        "explanation": "REST API integration timeout defaults to a maximum of 29 seconds (can be raised for Regional/private APIs via quota request). Use async patterns for long jobs.",
    },
    {
        "q": "An API Gateway REST API receives many identical GET requests. How can the developer reduce backend calls and latency with the LEAST effort?",
        "options": ["Enable API Gateway stage caching with an appropriate TTL", "Add ElastiCache in the Lambda function", "Enable Lambda provisioned concurrency", "Use a usage plan"],
        "answer": ["A"],
        "explanation": "API Gateway caching caches responses per stage (TTL default 300s, max 3600s). Clients can bypass with Cache-Control: max-age=0 if authorized.",
    },
    {
        "q": "An API must authenticate requests using a custom bearer token issued by a third-party identity system. Which API Gateway feature should be used?",
        "options": ["IAM authorization (SigV4)", "Lambda authorizer (token-based)", "Resource policy", "Usage plan"],
        "answer": ["B"],
        "explanation": "A Lambda (custom) authorizer validates custom tokens/headers and returns an IAM policy. For Cognito user pool JWTs, use a Cognito authorizer instead.",
    },
    {
        "q": "Mobile app users sign in with an Amazon Cognito user pool. The developer wants API Gateway to validate their tokens with the LEAST custom code. What should be used?",
        "options": ["Lambda authorizer", "Cognito user pool authorizer", "IAM authorization", "API keys"],
        "answer": ["B"],
        "explanation": "A Cognito user pool authorizer validates ID/access tokens natively without writing code.",
    },
    # ---------------- Security: IAM, STS, KMS, Secrets ----------------
    {
        "q": "An application must encrypt 50 MB files using AWS KMS. What is the correct approach?",
        "options": ["Call kms:Encrypt with the file", "Use envelope encryption: call GenerateDataKey, encrypt locally with the plaintext data key, store the encrypted data key with the file", "Split the file into 4 KB chunks and call Encrypt for each", "Export the KMS key and encrypt locally"],
        "answer": ["B"],
        "explanation": "KMS Encrypt handles at most 4 KB. Envelope encryption uses GenerateDataKey; the plaintext key encrypts data locally and is discarded, the encrypted key is stored alongside the data.",
    },
    {
        "q": "An application needs to store database credentials with automatic rotation every 30 days. Which service is the BEST fit?",
        "options": ["Systems Manager Parameter Store SecureString", "AWS Secrets Manager", "Lambda environment variables", "Amazon S3 with SSE-KMS"],
        "answer": ["B"],
        "explanation": "Secrets Manager has native rotation (built-in for RDS/Aurora/Redshift/DocumentDB, custom via Lambda). Parameter Store has no native rotation but is cheaper for config values.",
    },
    {
        "q": "An IAM policy has an explicit Allow for s3:GetObject, while an SCP attached to the account has an explicit Deny for the same action. What is the result?",
        "options": ["Allowed, because the IAM policy is more specific", "Denied, because an explicit deny always overrides an allow", "Allowed only for the root user", "It depends on the bucket policy"],
        "answer": ["B"],
        "explanation": "IAM evaluation: explicit Deny > explicit Allow > implicit deny (default).",
    },
    {
        "q": "A developer wants to test whether an IAM policy grants access to a specific API action without actually making the call. Which tools can help? (Select TWO.)",
        "options": ["IAM Policy Simulator", "The --dry-run parameter on supported CLI commands (e.g. EC2)", "AWS X-Ray", "Amazon Inspector", "AWS Trusted Advisor"],
        "answer": ["A", "B"],
        "explanation": "The IAM Policy Simulator evaluates policies; --dry-run checks permissions without performing the action (returns DryRunOperation if allowed).",
    },
    {
        "q": "A developer receives an encoded authorization failure message from an EC2 API call. How can the developer decode it?",
        "options": ["Use the sts decode-authorization-message command", "Use base64 decode", "Use kms decrypt", "Check CloudWatch Logs"],
        "answer": ["A"],
        "explanation": "sts:DecodeAuthorizationMessage decodes the message to show which policy/condition caused the denial.",
    },
    {
        "q": "An API requires MFA for sensitive operations. A developer using the CLI with IAM user credentials must obtain MFA-authenticated temporary credentials. Which STS API should be used?",
        "options": ["AssumeRoleWithWebIdentity", "GetSessionToken with SerialNumber and TokenCode", "GetFederationToken", "GetCallerIdentity"],
        "answer": ["B"],
        "explanation": "GetSessionToken (or AssumeRole) with MFA parameters returns temporary credentials that satisfy aws:MultiFactorAuthPresent conditions.",
    },
    {
        "q": "A developer wants the AWS CLI to show which IAM identity is currently being used. Which command?",
        "options": ["aws iam get-user", "aws sts get-caller-identity", "aws configure list-profiles", "aws iam list-roles"],
        "answer": ["B"],
        "explanation": "sts get-caller-identity returns the account, ARN and user ID of the current credentials — works for users and assumed roles and needs no permissions.",
    },
    {
        "q": "In what order does the AWS SDK default credential provider chain typically look for credentials?",
        "options": ["Instance profile → environment variables → shared credentials file", "Environment variables → shared credentials/config files → container/instance role credentials", "Shared credentials file → code → environment variables", "Only the instance profile"],
        "answer": ["B"],
        "explanation": "Explicit code config first, then environment variables (AWS_ACCESS_KEY_ID…), then ~/.aws/credentials & config (profiles, SSO), then ECS container credentials, then EC2 instance metadata (IMDS).",
    },
    # ---------------- Cognito ----------------
    {
        "q": "An application needs user sign-up/sign-in with email verification, MFA, and social login (Google, Facebook), returning JWTs to the app. Which service/feature?",
        "options": ["Cognito identity pools", "Cognito user pools", "IAM Identity Center", "AWS STS"],
        "answer": ["B"],
        "explanation": "User pools are the user directory/authentication service issuing ID, access and refresh tokens (JWT). Identity pools are for AWS credentials.",
    },
    {
        "q": "A developer wants to run custom validation logic during Cognito user pool sign-up (for example, only allow emails from a certain domain). What should be used?",
        "options": ["A Cognito user pool Lambda trigger (Pre sign-up)", "An API Gateway authorizer", "An IAM policy condition", "AWS WAF"],
        "answer": ["A"],
        "explanation": "User pool Lambda triggers (Pre sign-up, Post confirmation, Pre token generation, etc.) customize the authentication flow.",
    },
    # ---------------- CloudFormation / SAM / CDK ----------------
    {
        "q": "Stack A creates a VPC. Stack B must reference the VPC ID. What should be used?",
        "options": ["Parameters in stack A", "Outputs with Export in stack A and Fn::ImportValue in stack B", "Mappings", "Conditions"],
        "answer": ["B"],
        "explanation": "Cross-stack references: export an output value and import it with Fn::ImportValue. An exported value can't be deleted while imported.",
    },
    {
        "q": "A CloudFormation template must use a different AMI ID depending on the Region it's deployed in. Which section should be used?",
        "options": ["Parameters", "Mappings with Fn::FindInMap", "Outputs", "Transform"],
        "answer": ["B"],
        "explanation": "Mappings define static lookup tables (e.g. Region → AMI) read with Fn::FindInMap and AWS::Region. SSM public parameters are another option.",
    },
    {
        "q": "A developer wants to keep an RDS database's data when its CloudFormation stack is deleted, preferably as a snapshot. What should be set?",
        "options": ["DeletionPolicy: Snapshot", "UpdateReplacePolicy: Delete", "A stack policy", "Termination protection only"],
        "answer": ["A"],
        "explanation": "DeletionPolicy (Delete | Retain | Snapshot) controls what happens to a resource on stack deletion. Snapshot is supported for RDS, EBS, ElastiCache, Redshift, etc.",
    },
    {
        "q": "A CloudFormation template launches an EC2 instance that must finish installing software before the stack reports CREATE_COMPLETE. What should be used?",
        "options": ["DependsOn", "A CreationPolicy / WaitCondition with cfn-signal", "Outputs", "Fn::GetAtt"],
        "answer": ["B"],
        "explanation": "cfn-signal sends a success/failure signal after user data/cfn-init completes; the CreationPolicy waits for it (with a timeout).",
    },
    {
        "q": "Which SAM CLI commands build and deploy a serverless application? (Select TWO.)",
        "options": ["sam build", "sam deploy", "sam publish-stack", "cfn-init", "sam compile"],
        "answer": ["A", "B"],
        "explanation": "sam build prepares artifacts; sam deploy (--guided the first time) packages to S3 and deploys the CloudFormation stack. sam local invoke / start-api run functions locally.",
    },
    {
        "q": "In a SAM template, which properties enable automatic gradual traffic shifting for a Lambda function? (Select TWO.)",
        "options": ["AutoPublishAlias", "DeploymentPreference", "ReservedConcurrentExecutions", "Layers", "CodeUri"],
        "answer": ["A", "B"],
        "explanation": "AutoPublishAlias publishes a new version and points an alias to it; DeploymentPreference (e.g. Canary10Percent5Minutes) uses CodeDeploy to shift traffic with alarms & hooks.",
    },
    {
        "q": "Which AWS CDK command generates the CloudFormation template from the CDK app without deploying?",
        "options": ["cdk deploy", "cdk synth", "cdk bootstrap", "cdk diff"],
        "answer": ["B"],
        "explanation": "cdk synth synthesizes CloudFormation. cdk bootstrap provisions the staging resources (S3 bucket, roles) needed once per account/Region; cdk diff compares with the deployed stack.",
    },
    # ---------------- CI/CD ----------------
    {
        "q": "Where must the buildspec.yml file be located by default for AWS CodeBuild?",
        "options": ["In an S3 bucket named buildspec", "In the root of the source code directory", "In the .ebextensions folder", "In the CodePipeline artifact store"],
        "answer": ["B"],
        "explanation": "CodeBuild looks for buildspec.yml at the source root unless you override the name/location in the project settings.",
    },
    {
        "q": "In a CodeDeploy Lambda deployment, which lifecycle hooks can run validation Lambda functions? (Select TWO.)",
        "options": ["BeforeAllowTraffic", "AfterAllowTraffic", "ApplicationStop", "BeforeInstall", "ValidateService"],
        "answer": ["A", "B"],
        "explanation": "Lambda (and ECS) deployments support BeforeAllowTraffic and AfterAllowTraffic hooks. ApplicationStop/BeforeInstall/ValidateService are EC2/on-prem hooks.",
    },
    {
        "q": "Which CodeDeploy deployment configuration shifts 10% of Lambda traffic every minute until all traffic is shifted?",
        "options": ["LambdaCanary10Percent10Minutes", "LambdaLinear10PercentEvery1Minute", "LambdaAllAtOnce", "LambdaCanary10Percent5Minutes"],
        "answer": ["B"],
        "explanation": "Linear shifts equal increments at equal intervals. Canary shifts a fixed % first, then the remainder after the interval. AllAtOnce shifts immediately.",
    },
    {
        "q": "A CodeBuild project must speed up builds by reusing downloaded dependencies between builds. What should be configured?",
        "options": ["Build caching (S3 or local cache)", "A larger compute type only", "Artifacts encryption", "VPC configuration"],
        "answer": ["A"],
        "explanation": "CodeBuild caching (S3 cache or local source/Docker layer/custom cache) stores reusable files like dependencies between builds.",
    },
    {
        "q": "An Elastic Beanstalk application needs to install packages and configure settings during environment creation. Where should these configuration files go?",
        "options": ["In the .ebextensions folder as .config files at the root of the source bundle", "In buildspec.yml", "In appspec.yml", "In the Dockerrun.aws.json file only"],
        "answer": ["A"],
        "explanation": ".ebextensions/*.config (YAML/JSON) customizes packages, files, commands, container_commands, option settings and resources.",
    },
    {
        "q": "An Elastic Beanstalk application must run long-running background jobs pulled from a queue, separate from the web tier. What should be used?",
        "options": ["A web server environment with cron", "A worker environment (uses SQS; periodic tasks via cron.yaml)", "Lambda@Edge", "An Elastic Beanstalk swap URL"],
        "answer": ["B"],
        "explanation": "Worker environments run a daemon that pulls messages from SQS and POSTs them to your app. cron.yaml defines periodic tasks.",
    },
    {
        "q": "Which Elastic Beanstalk deployment policy is the FASTEST but causes downtime?",
        "options": ["All at once", "Rolling", "Rolling with additional batch", "Immutable"],
        "answer": ["A"],
        "explanation": "All at once deploys to all instances simultaneously — fastest, but the app is unavailable during the deployment and rollback requires a redeploy.",
    },
    # ---------------- Monitoring ----------------
    {
        "q": "A developer wants to add searchable key-value data (such as user ID) to X-Ray traces so traces can be filtered by it. What should be used?",
        "options": ["Metadata", "Annotations", "Segments documents only", "Sampling rules"],
        "answer": ["B"],
        "explanation": "Annotations are indexed key-value pairs usable in filter expressions. Metadata is not indexed — for storing extra data you don't need to search on.",
    },
    {
        "q": "A developer wants to enable X-Ray tracing for a Lambda function with minimal effort. What should be done? (Select TWO.)",
        "options": ["Enable active tracing on the function", "Ensure the execution role has X-Ray write permissions (AWSXRayDaemonWriteAccess)", "Install the X-Ray daemon on the function", "Create a VPC endpoint", "Enable CloudTrail data events"],
        "answer": ["A", "B"],
        "explanation": "Lambda runs the X-Ray daemon for you; just turn on active tracing and grant permissions. Use the X-Ray SDK/ADOT to trace downstream calls.",
    },
    {
        "q": "A Lambda function needs to generate custom CloudWatch metrics asynchronously without making PutMetricData API calls. What should be used?",
        "options": ["CloudWatch Embedded Metric Format (EMF) in structured logs", "CloudWatch Logs Insights", "X-Ray annotations", "CloudTrail"],
        "answer": ["A"],
        "explanation": "EMF writes metrics as specially formatted JSON log lines; CloudWatch extracts them as metrics automatically — no extra API calls or latency.",
    },
    {
        "q": "A developer needs to publish a custom metric at 1-second granularity. What should be specified?",
        "options": ["StorageResolution = 1 (high-resolution metric)", "Period = 60", "Detailed monitoring", "A metric filter"],
        "answer": ["A"],
        "explanation": "High-resolution custom metrics (StorageResolution 1) support 1-second granularity. Standard resolution is 60 seconds.",
    },
    {
        "q": "Which service records API calls made in an AWS account (who did what, when, from where)?",
        "options": ["Amazon CloudWatch", "AWS CloudTrail", "AWS X-Ray", "AWS Config"],
        "answer": ["B"],
        "explanation": "CloudTrail logs management (and optionally data) API events for auditing. Config tracks resource configuration changes; CloudWatch covers metrics/logs.",
    },
    {
        "q": "A developer needs to query and analyze CloudWatch log data interactively with a purpose-built query language to find the top 10 slowest requests. Which feature?",
        "options": ["CloudWatch Logs Insights", "CloudWatch metric math", "CloudTrail Lake", "X-Ray Analytics"],
        "answer": ["A"],
        "explanation": "Logs Insights runs interactive queries (fields, filter, stats, sort, limit) across log groups.",
    },
    # ---------------- Containers / Step Functions / Other ----------------
    {
        "q": "A developer wants to run containers on ECS without managing EC2 instances. Which launch type should be used?",
        "options": ["EC2 launch type", "AWS Fargate launch type", "External launch type", "Elastic Beanstalk single container"],
        "answer": ["B"],
        "explanation": "Fargate is serverless compute for containers — you specify CPU/memory in the task definition, no servers to manage.",
    },
    {
        "q": "In ECS, what is the difference between the task execution role and the task role?",
        "options": ["They are the same", "The task execution role lets the ECS agent pull images from ECR and write logs; the task role grants permissions to the application code in the container", "The task role is used by the ECS agent; the execution role is used by the application", "The task execution role is only for Fargate Spot"],
        "answer": ["B"],
        "explanation": "Execution role = ECS/Fargate agent (ECR pull, CloudWatch Logs, secrets retrieval). Task role = your application's AWS API calls.",
    },
    {
        "q": "A Step Functions workflow must wait for a human approval that could take days before continuing. Which integration pattern should be used?",
        "options": ["Request Response", "Run a Job (.sync)", "Wait for a Callback with a task token (.waitForTaskToken)", "Express Workflow"],
        "answer": ["C"],
        "explanation": "The callback pattern pauses the task until SendTaskSuccess/SendTaskFailure is called with the task token. Standard workflows can run up to 1 year.",
    },
    {
        "q": "A high-volume event-processing workflow runs thousands of times per second and each execution completes in under 5 minutes. Which Step Functions type is most cost-effective?",
        "options": ["Standard Workflows", "Express Workflows", "Activity tasks", "Map state"],
        "answer": ["B"],
        "explanation": "Express Workflows are for high-volume, short (≤5 min) executions with at-least-once semantics and duration-based pricing. Standard: up to 1 year, exactly-once, priced per state transition.",
    },
    {
        "q": "A developer needs a managed GraphQL API that can combine data from DynamoDB, Lambda, and HTTP sources with real-time subscriptions. Which service?",
        "options": ["Amazon API Gateway REST API", "AWS AppSync", "Amazon Cognito", "AWS Amplify Hosting"],
        "answer": ["B"],
        "explanation": "AppSync is a managed GraphQL (and Pub/Sub) service with resolvers for many data sources and real-time subscriptions via WebSockets.",
    },
    {
        "q": "With the lazy-loading (cache-aside) strategy in ElastiCache, what is a known disadvantage?",
        "options": ["Every write is slower", "Cache misses cause extra latency and data can become stale", "Cache is filled with data that's never read", "It cannot use TTL"],
        "answer": ["B"],
        "explanation": "Lazy loading: only requested data is cached, but a miss costs 3 trips and data can be stale (use TTL). Write-through keeps data fresh but caches data that may never be read and adds write latency.",
    },
    {
        "q": "An application running on EC2 needs to read configuration values in a hierarchy (e.g. /myapp/prod/db-url) with versioning and at no additional cost for standard parameters. Which service?",
        "options": ["AWS Secrets Manager", "AWS Systems Manager Parameter Store", "AWS AppConfig only", "Amazon S3"],
        "answer": ["B"],
        "explanation": "Parameter Store supports hierarchies, versioning, SecureString (KMS) and is free for standard parameters. GetParametersByPath reads a whole hierarchy.",
    },
    {
        "q": "Which exam-relevant service lets a developer build, deploy and host full-stack web and mobile apps with Git-based CI/CD and built-in auth/API backends?",
        "options": ["AWS Amplify", "AWS CodeStar", "AWS Elastic Beanstalk", "Amazon Lightsail"],
        "answer": ["A"],
        "explanation": "AWS Amplify (Hosting + Gen 2 backends) provides Git-based CI/CD hosting for frontends and managed backends (Cognito, AppSync, DynamoDB, S3).",
    },
    {
        "q": "An EC2-hosted application needs to retrieve the instance's ID at runtime. How should it get it?",
        "options": ["Call http://169.254.169.254/latest/meta-data/instance-id (IMDSv2 with a session token)", "Call http://169.254.169.254/latest/user-data", "Use the DescribeInstances API without filters", "Read it from /etc/instance-id"],
        "answer": ["A"],
        "explanation": "Instance metadata (IMDS) at 169.254.169.254 exposes instance-id, role credentials etc. IMDSv2 requires a PUT to get a session token first. user-data is the launch script.",
    },
]

TOPIC_RULES = [
    ("Lambda", r"\blambda\b"),
    ("DynamoDB", r"dynamodb|\bdax\b"),
    ("S3", r"\bs3\b"),
    ("API Gateway", r"api gateway"),
    ("SQS / SNS", r"\bsqs\b|\bsns\b"),
    ("Kinesis", r"kinesis|firehose"),
    ("Cognito", r"cognito"),
    ("IAM / STS", r"\biam\b|\bsts\b|assumerole|access key|least privilege|credential"),
    ("KMS / Encryption", r"\bkms\b|encrypt|secrets manager|parameter store"),
    ("CloudFormation / SAM / CDK", r"cloudformation|\bsam\b|\bcdk\b|swagger"),
    ("CI/CD (Code*)", r"codedeploy|codebuild|codepipeline|codecommit|appspec|buildspec"),
    ("Elastic Beanstalk", r"beanstalk"),
    ("Monitoring (CloudWatch / X-Ray)", r"cloudwatch|x-ray|xray|cloudtrail|log"),
    ("Containers (ECS)", r"\becs\b|container|fargate|docker"),
    ("Step Functions / EventBridge", r"step functions|state machine|eventbridge"),
    ("Caching / Databases", r"elasticache|\brds\b|aurora|cache"),
    ("CloudFront / Networking", r"cloudfront|\bvpc\b|load balancer|\balb\b|route 53"),
]


def topics_for(text):
    t = text.lower()
    found = [name for name, pat in TOPIC_RULES if re.search(pat, t)]
    return found[:3] or ["General"]


def parse_txt(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n")
    blocks = re.split(r"(?m)^Q(\d+)[ \t]*", raw)
    # blocks = [preamble, num, body, num, body, ...]
    out, seen_ids = [], set()
    for i in range(1, len(blocks), 2):
        num, body = blocks[i], blocks[i + 1]
        if "Options:" not in body:
            continue
        qid = num
        while qid in seen_ids:
            qid += "b"
        seen_ids.add(qid)

        q_text, rest = body.split("Options:", 1)
        m = re.search(r"(?m)^Correct Answer", rest)
        if not m:
            continue
        opts_part, ans_part = rest[: m.start()], rest[m.start():]

        options = []
        for line in opts_part.split("\n"):
            om = re.match(r"^\s*([A-F])\.\s*(.+)$", line)
            if om:
                options.append(om.group(2).strip())
            elif options and line.strip():
                options[-1] += " " + line.strip()
        answers = sorted(set(re.findall(r"(?m)^\s*([A-F])\.", ans_part)))
        if not options or not answers:
            continue

        # tidy question text: strip trailing whitespace and the stray "json" marker line
        q_lines = [l.rstrip() for l in q_text.strip().split("\n")]
        q_lines = [l for l in q_lines if l.strip().lower() != "json"]
        q_clean = re.sub(r"\n{3,}", "\n\n", "\n".join(q_lines)).strip()

        out.append({"id": qid, "q": q_clean, "options": options, "answer": answers})
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())[:160]


def main():
    questions, seen = [], set()
    for path in sorted(glob.glob(os.path.join(HERE, "*.txt"))):
        for item in parse_txt(path):
            key = norm(item["q"])
            if key in seen:
                continue
            seen.add(key)
            qid = item["id"]
            answer = ANSWER_OVERRIDES.get(qid, item["answer"])
            questions.append({
                "id": "F" + qid,
                "source": "file",
                "label": "Q" + qid,
                "q": item["q"],
                "options": item["options"],
                "answer": [ord(a) - 65 for a in answer],
                "explanation": EXPLANATIONS.get(qid, ""),
                "topics": topics_for(item["q"] + " " + " ".join(item["options"])),
            })
    n_file = len(questions)

    for i, e in enumerate(EXTRA, 1):
        key = norm(e["q"])
        if key in seen:
            continue
        seen.add(key)
        questions.append({
            "id": "X%d" % i,
            "source": "extra",
            "label": "DVA-%d" % i,
            "q": e["q"],
            "options": e["options"],
            "answer": [ord(a) - 65 for a in e["answer"]],
            "explanation": e["explanation"],
            "topics": topics_for(e["q"] + " " + " ".join(e["options"])),
        })

    js = "// Generated by build_questions.py - do not edit by hand.\nwindow.QUESTIONS = " + \
        json.dumps(questions, ensure_ascii=False, indent=1) + ";\n"
    with open(os.path.join(HERE, "questions.js"), "w", encoding="utf-8") as f:
        f.write(js)
    print("Wrote questions.js: %d from .txt (duplicates removed), %d extra, %d total"
          % (n_file, len(questions) - n_file, len(questions)))


if __name__ == "__main__":
    main()
