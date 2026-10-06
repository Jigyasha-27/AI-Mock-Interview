import streamlit as st
import speech_recognition as sr
import tempfile
import os
import subprocess
import random
import hashlib
import time
import re
import wave
from collections import Counter
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

import cv2
import numpy as np

from streamlit_webrtc import webrtc_streamer
from pypdf import PdfReader
from docx import Document
from deepface import DeepFace


# =========================================================
# OPTIONAL PDF LIBRARY
# =========================================================

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        KeepTogether,
    )
    from reportlab.lib import colors

    REPORTLAB_AVAILABLE = True

except ImportError:
    REPORTLAB_AVAILABLE = False


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Mock Interview Simulator",
    page_icon="🎤",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f7f9fc;
}

.title {
    text-align: center;
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #666;
    font-size: 18px;
    margin-bottom: 25px;
}

.metric-card {
    background: white;
    padding: 18px;
    border-radius: 15px;
    border: 1px solid #e7e7e7;
    text-align: center;
    margin-bottom: 10px;
}

.metric-value {
    font-size: 30px;
    font-weight: 700;
}

.metric-label {
    color: #666;
    font-size: 14px;
}

.question-box {
    background: black;
    padding: 25px;
    border-radius: 15px;
    border-left: 5px solid #4f46e5;
    margin-bottom: 20px;
    color: white;
}
.question-box h3 {
    color: white;
}

.answer-box {
    background: #ffffff;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #dbeafe;
    margin-top: 10px;
    margin-bottom: 12px;
}

.best-answer-box {
    background: #f0fdf4;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #bbf7d0;
    margin-top: 10px;
    margin-bottom: 18px;
}

.report-box {
    background: white;
    padding: 22px;
    border-radius: 15px;
    border: 1px solid #e5e7eb;
    margin-bottom: 18px;
}

.warning-box {
    background: #fff8e1;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #ffe082;
}

.good-box {
    background: #eefbf3;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #b7e4c7;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# CONSTANTS
# =========================================================

FFMPEG_PATH = (
    r"C:\Users\Nitin\Downloads\ffmpeg-9.0.2-essentials_build"
    r"\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"
)

HAAR_CASCADE_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "haarcascade_frontalface_default.xml"
)

FILLER_WORDS = [
    "um",
    "uh",
    "umm",
    "uhh",
    "like",
    "you know",
    "actually",
    "basically",
    "i mean",
    "sort of",
    "kind of"
]


# =========================================================
# QUESTION BANK
# =========================================================

QUESTION_BANK = {

    "Software Developer": {

        "Technical": {

            "Easy": [
                "What is a variable in programming?",
                "What is an array?",
                "What is a function?",
                "What is OOP?",
                "What is a database?",
                "What is SQL?"
            ],

            "Medium": [
                "Explain the four pillars of OOP.",
                "What is the difference between an array and a linked list?",
                "What is the difference between SQL and NoSQL?",
                "Explain inheritance and polymorphism.",
                "How do you approach problem solving in programming?",
                "What is the difference between a stack and a queue?"
            ],

            "Hard": [
                "How would you optimize an application that is becoming slow?",
                "Explain time complexity and why it matters.",
                "How would you design a scalable backend?",
                "How would you debug a problem occurring in production?",
                "How does database indexing improve performance?",
                "How would you handle millions of requests in an application?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose IT?",
                "What are your strengths?",
                "What are your hobbies?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?",
                "What is your weakness?"
            ],

            "Hard": [
                "Why should we select you over another candidate?",
                "Tell me about a failure and what you learned from it.",
                "How would you handle a disagreement with a teammate?",
                "Where do you see yourself in five years?"
            ]
        }
    },


    "Python Developer": {

        "Technical": {

            "Easy": [
                "What is Python?",
                "What is a list in Python?",
                "What is a dictionary in Python?",
                "What is a function in Python?",
                "What is the difference between a list and a tuple?"
            ],

            "Medium": [
                "What is a lambda function?",
                "What is list comprehension?",
                "How does exception handling work in Python?",
                "What is the difference between shallow copy and deep copy?",
                "What are decorators in Python?"
            ],

            "Hard": [
                "How does memory management work in Python?",
                "What are generators and why are they useful?",
                "How would you optimize a slow Python application?",
                "What is the difference between threading and multiprocessing?",
                "How would you build a scalable Python backend?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose Python?",
                "What are your strengths?",
                "What is your most important project?"
            ],

            "Medium": [
                "How do you handle deadlines?",
                "Tell me about a challenging project.",
                "Why should we hire you?",
                "How do you handle pressure?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we hire you as a Python developer?"
            ]
        }
    },


    "Java Developer": {

        "Technical": {

            "Easy": [
                "What is Java?",
                "What is a class and object?",
                "What is inheritance?",
                "What is encapsulation?",
                "What is polymorphism?"
            ],

            "Medium": [
                "What is the difference between JDK, JRE and JVM?",
                "What is method overloading and overriding?",
                "How does exception handling work in Java?",
                "What is an interface and abstract class?",
                "Explain the four pillars of OOP."
            ],

            "Hard": [
                "How does garbage collection work in Java?",
                "How does multithreading work in Java?",
                "How would you optimize a slow Java application?",
                "Explain the Java memory model.",
                "How would you design a scalable Java backend?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose Java?",
                "What are your strengths?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we hire you as a Java developer?"
            ]
        }
    },


    "Web Developer": {

        "Technical": {

            "Easy": [
                "What is HTML?",
                "What is CSS?",
                "What is JavaScript?",
                "What is a website?",
                "What is the difference between frontend and backend?"
            ],

            "Medium": [
                "What is responsive web design?",
                "What is an API?",
                "What is the difference between GET and POST?",
                "What is the DOM?",
                "What is the difference between authentication and authorization?"
            ],

            "Hard": [
                "How would you optimize a slow website?",
                "Explain how browser rendering works.",
                "How would you design a scalable web application?",
                "What are common web security vulnerabilities?",
                "How would you improve website performance?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose web development?",
                "What are your strengths?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we select you as a web developer?"
            ]
        }
    },


    "Data Analyst": {

        "Technical": {

            "Easy": [
                "What is data analysis?",
                "What is SQL?",
                "What is a database?",
                "What are mean and median?",
                "What is data visualization?"
            ],

            "Medium": [
                "Explain mean, median and mode.",
                "How do you handle missing data?",
                "Explain SQL joins.",
                "Which Python libraries are commonly used for data analysis?",
                "What is the difference between correlation and causation?"
            ],

            "Hard": [
                "How would you analyze a dataset containing millions of rows?",
                "How do you handle outliers?",
                "How would you explain a complex analysis to a non-technical person?",
                "How would you validate a dataset?",
                "How would you design an effective dashboard?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose data analytics?",
                "What are your strengths?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we select you as a data analyst?"
            ]
        }
    },


    "AI/ML Engineer": {

        "Technical": {

            "Easy": [
                "What is Artificial Intelligence?",
                "What is Machine Learning?",
                "What is supervised learning?",
                "What is a dataset?",
                "What is a feature?"
            ],

            "Medium": [
                "What is the difference between supervised and unsupervised learning?",
                "What is overfitting?",
                "What is underfitting?",
                "What is the difference between classification and regression?",
                "Why do we split data into training and testing sets?"
            ],

            "Hard": [
                "How would you handle an imbalanced dataset?",
                "Explain the bias-variance tradeoff.",
                "What would you do if your model performs poorly during validation?",
                "How would you deploy a machine learning model?",
                "How would you monitor a machine learning model in production?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose AI and ML?",
                "What are your strengths?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we select you as an AI/ML engineer?"
            ]
        }
    },


    "Database Developer": {

        "Technical": {

            "Easy": [
                "What is a database?",
                "What is SQL?",
                "What is a primary key?",
                "What is a foreign key?",
                "What is a table?"
            ],

            "Medium": [
                "What is normalization?",
                "Explain SQL joins.",
                "What is a database index?",
                "What is the difference between DELETE, DROP and TRUNCATE?",
                "What is a database transaction?"
            ],

            "Hard": [
                "How would you optimize a slow SQL query?",
                "How does indexing affect database performance?",
                "How would you design a database for a large application?",
                "What is database sharding?",
                "How would you design a scalable database?"
            ]
        },

        "HR": {

            "Easy": [
                "Tell me about yourself.",
                "Why did you choose database development?",
                "What are your strengths?"
            ],

            "Medium": [
                "Why should we hire you?",
                "Tell me about a challenging project.",
                "How do you handle pressure?",
                "How do you work in a team?"
            ],

            "Hard": [
                "Where do you see yourself in five years?",
                "Tell me about a failure.",
                "Why should we select you as a database developer?"
            ]
        }
    }
}


# =========================================================
# KEY CONCEPTS
# =========================================================

QUESTION_KEYWORDS = {

    "What is a variable in programming?":
        ["variable", "value", "memory", "store", "data"],

    "What is an array?":
        ["array", "collection", "elements", "index", "memory"],

    "What is a function?":
        ["function", "block", "code", "reuse", "input", "output", "parameter", "return"],

    "What is OOP?":
        ["object", "oriented", "class", "object", "programming"],

    "What is a database?":
        ["database", "data", "store", "organized", "manage", "retrieve"],

    "What is SQL?":
        ["sql", "query", "database", "structured", "data"],

    "Explain the four pillars of OOP.":
        ["encapsulation", "inheritance", "polymorphism", "abstraction"],

    "What is the difference between an array and a linked list?":
        ["array", "linked", "list", "memory", "contiguous", "node", "index"],

    "What is the difference between SQL and NoSQL?":
        ["sql", "nosql", "relational", "document", "schema", "database"],

    "Explain inheritance and polymorphism.":
        ["inheritance", "polymorphism", "class", "parent", "child", "method"],

    "What is the difference between a stack and a queue?":
        ["stack", "queue", "lifo", "fifo"],

    "What is Python?":
        ["python", "programming", "language", "interpreted"],

    "What is a list in Python?":
        ["list", "python", "ordered", "mutable", "elements"],

    "What is a dictionary in Python?":
        ["dictionary", "key", "value", "python"],

    "What is a function in Python?":
        ["function", "def", "code", "reuse", "parameter", "return"],

    "What is the difference between a list and a tuple?":
        ["list", "tuple", "mutable", "immutable"],

    "What is a lambda function?":
        ["lambda", "anonymous", "function", "expression"],

    "What is list comprehension?":
        ["list", "comprehension", "loop", "expression"],

    "How does exception handling work in Python?":
        ["exception", "try", "except", "finally", "error"],

    "What is the difference between shallow copy and deep copy?":
        ["shallow", "deep", "copy", "reference", "nested"],

    "What are decorators in Python?":
        ["decorator", "function", "wrapper", "modify"],

    "What is Java?":
        ["java", "programming", "language", "object", "oriented"],

    "What is a class and object?":
        ["class", "object", "blueprint", "instance"],

    "What is inheritance?":
        ["inheritance", "parent", "child", "class"],

    "What is encapsulation?":
        ["encapsulation", "data", "hiding", "class", "private"],

    "What is polymorphism?":
        ["polymorphism", "many", "forms", "method"],

    "What is the difference between JDK, JRE and JVM?":
        ["jdk", "jre", "jvm", "development", "runtime", "virtual"],

    "What is method overloading and overriding?":
        ["overloading", "overriding", "method", "compile", "runtime"],

    "How does exception handling work in Java?":
        ["exception", "try", "catch", "finally", "throw"],

    "What is an interface and abstract class?":
        ["interface", "abstract", "class", "method"],

    "What is HTML?":
        ["html", "markup", "structure", "web", "tags"],

    "What is CSS?":
        ["css", "style", "design", "web", "layout"],

    "What is JavaScript?":
        ["javascript", "language", "web", "interactive", "browser"],

    "What is a website?":
        ["website", "web", "pages", "browser", "server"],

    "What is the difference between frontend and backend?":
        ["frontend", "backend", "client", "server"],

    "What is responsive web design?":
        ["responsive", "design", "screen", "device", "layout"],

    "What is an API?":
        ["api", "application", "interface", "communication", "request", "response"],

    "What is the difference between GET and POST?":
        ["get", "post", "request", "data", "server"],

    "What is the DOM?":
        ["dom", "document", "object", "model", "html"],

    "What is the difference between authentication and authorization?":
        ["authentication", "authorization", "identity", "permission"],

    "What is data analysis?":
        ["data", "analysis", "insight", "pattern"],

    "What are mean and median?":
        ["mean", "median", "average", "middle"],

    "What is data visualization?":
        ["visualization", "data", "chart", "graph"],

    "Explain mean, median and mode.":
        ["mean", "median", "mode"],

    "How do you handle missing data?":
        ["missing", "data", "remove", "impute", "mean", "median"],

    "Explain SQL joins.":
        ["join", "sql", "inner", "left", "right", "table"],

    "What is the difference between correlation and causation?":
        ["correlation", "causation", "relationship", "cause"],

    "What is Artificial Intelligence?":
        ["artificial", "intelligence", "machine", "computer"],

    "What is Machine Learning?":
        ["machine", "learning", "data", "model", "prediction"],

    "What is supervised learning?":
        ["supervised", "learning", "label", "data", "model"],

    "What is a dataset?":
        ["dataset", "data", "records", "samples"],

    "What is a feature?":
        ["feature", "input", "variable", "model"],

    "What is the difference between supervised and unsupervised learning?":
        ["supervised", "unsupervised", "label", "data"],

    "What is overfitting?":
        ["overfitting", "training", "data", "generalization"],

    "What is underfitting?":
        ["underfitting", "model", "simple", "training"],

    "What is the difference between classification and regression?":
        ["classification", "regression", "categorical", "continuous"],

    "Why do we split data into training and testing sets?":
        ["training", "testing", "data", "model", "evaluation"],

    "What is a primary key?":
        ["primary", "key", "unique", "row", "table"],

    "What is a foreign key?":
        ["foreign", "key", "relationship", "table"],

    "What is a table?":
        ["table", "rows", "columns", "data"],

    "What is normalization?":
        ["normalization", "database", "redundancy", "tables"],

    "What is a database index?":
        ["index", "database", "search", "performance"],

    "What is the difference between DELETE, DROP and TRUNCATE?":
        ["delete", "drop", "truncate", "table", "rows"],

    "What is a database transaction?":
        ["transaction", "commit", "rollback", "acid"],

    "Tell me about yourself.":
        ["name", "education", "skills", "project", "experience", "goal"]
}


# =========================================================
# BEST FITTING ANSWERS
# =========================================================

BEST_FITTING_ANSWERS = {

    # -----------------------------------------------------
    # COMMON TECHNICAL
    # -----------------------------------------------------

    "What is a variable in programming?":
        "A variable is a named storage location used to hold a value in a program. "
        "The value can represent data such as a number, text, or Boolean value and may change during program execution.",

    "What is an array?":
        "An array is a data structure that stores multiple elements of the same or compatible type in an ordered collection. "
        "Elements are accessed using an index, which makes accessing a particular element efficient.",

    "What is a function?":
        "A function is a reusable block of code designed to perform a specific task. "
        "It can accept inputs through parameters and may return a result, which helps make programs modular and easier to maintain.",

    "What is OOP?":
        "OOP stands for Object-Oriented Programming. It is a programming approach that organizes software around objects and classes. "
        "Its main concepts include encapsulation, inheritance, polymorphism, and abstraction.",

    "What is a database?":
        "A database is an organized collection of data that can be stored, managed, searched, and retrieved efficiently. "
        "Database management systems such as MySQL, Oracle, and PostgreSQL provide tools to work with this data.",

    "What is SQL?":
        "SQL stands for Structured Query Language. It is used to create, retrieve, update, and manage data in relational databases. "
        "Common SQL operations include SELECT, INSERT, UPDATE, and DELETE.",

    "Explain the four pillars of OOP.":
        "The four pillars of OOP are encapsulation, inheritance, polymorphism, and abstraction. "
        "Encapsulation combines data and methods, inheritance allows reuse from existing classes, polymorphism allows the same interface to have different implementations, and abstraction hides unnecessary implementation details.",

    "What is the difference between an array and a linked list?":
        "An array stores elements in contiguous memory and provides fast index-based access. "
        "A linked list stores elements in nodes connected through links, so it can grow dynamically and allows efficient insertion or deletion at known positions, but direct access is slower.",

    "What is the difference between SQL and NoSQL?":
        "SQL databases are generally relational and organize data into tables with a structured schema. "
        "NoSQL databases use models such as documents, key-value pairs, or graphs and are often more flexible for unstructured or rapidly changing data.",

    "Explain inheritance and polymorphism.":
        "Inheritance allows a child class to acquire properties and methods from a parent class. "
        "Polymorphism allows the same method or interface to behave differently depending on the object or implementation being used.",

    "How do you approach problem solving in programming?":
        "I first understand the problem and identify the required input and output. "
        "Then I break the problem into smaller parts, consider possible approaches, choose an efficient algorithm, implement it, test edge cases, and optimize the solution if necessary.",

    "What is the difference between a stack and a queue?":
        "A stack follows the LIFO principle, meaning the last element inserted is the first one removed. "
        "A queue follows FIFO, meaning the first element inserted is the first one removed. Stacks are commonly used for recursion and undo operations, while queues are useful for scheduling and buffering.",

    # -----------------------------------------------------
    # SOFTWARE HARD
    # -----------------------------------------------------

    "How would you optimize an application that is becoming slow?":
        "I would first identify the bottleneck using profiling, logs, and performance metrics instead of optimizing blindly. "
        "Then I would optimize inefficient algorithms and database queries, introduce caching where appropriate, reduce unnecessary network calls, and test the application again to verify the improvement.",

    "Explain time complexity and why it matters.":
        "Time complexity describes how the running time of an algorithm grows as the input size increases. "
        "It matters because it helps compare algorithms and choose solutions that can handle large inputs efficiently. For example, O(n) generally scales better than O(n²) for large datasets.",

    "How would you design a scalable backend?":
        "I would design the backend using modular services, efficient APIs, proper database indexing, caching, and horizontal scaling where required. "
        "Load balancing, asynchronous processing, monitoring, logging, and fault tolerance would also be important for handling increasing traffic reliably.",

    "How would you debug a problem occurring in production?":
        "I would first reproduce or understand the issue using logs, monitoring data, error traces, and recent deployment changes. "
        "I would identify the root cause, apply the smallest safe fix, test it, deploy carefully, and monitor the system afterward to ensure the issue is resolved.",

    "How does database indexing improve performance?":
        "An index creates an additional data structure that allows the database to find rows more efficiently without scanning the entire table. "
        "Indexes can significantly improve read and search operations, although they require additional storage and can increase the cost of insert and update operations.",

    "How would you handle millions of requests in an application?":
        "I would use horizontal scaling with multiple application instances behind a load balancer. "
        "I would also use caching, database optimization, connection pooling, asynchronous processing, rate limiting, and monitoring to handle high traffic while maintaining reliability.",

    # -----------------------------------------------------
    # PYTHON
    # -----------------------------------------------------

    "What is Python?":
        "Python is a high-level, interpreted, general-purpose programming language known for its readable syntax and large ecosystem. "
        "It is widely used in web development, automation, data analysis, artificial intelligence, and scripting.",

    "What is a list in Python?":
        "A list is an ordered and mutable collection in Python. "
        "It can store multiple values, including values of different types, and supports operations such as indexing, slicing, insertion, deletion, and iteration.",

    "What is a dictionary in Python?":
        "A dictionary is a mutable collection that stores data as key-value pairs. "
        "Keys are used to access their corresponding values, making dictionaries useful for fast lookups and structured data.",

    "What is a function in Python?":
        "A function in Python is a reusable block of code defined using the def keyword. "
        "It can accept parameters, perform a task, and optionally return a value. Functions improve code reuse and organization.",

    "What is the difference between a list and a tuple?":
        "A list is mutable, so its elements can be changed after creation. "
        "A tuple is immutable, meaning its elements cannot be changed after creation. Tuples are useful for fixed collections of values.",

    "What is a lambda function?":
        "A lambda function is a small anonymous function defined using the lambda keyword. "
        "It can take arguments and return an expression result and is commonly used for short operations with functions such as map, filter, and sorted.",

    "What is list comprehension?":
        "List comprehension is a concise way to create a new list from an iterable. "
        "It can include a loop and an optional condition, making simple transformations more readable than a traditional multi-line loop.",

    "How does exception handling work in Python?":
        "Python handles exceptions using try, except, else, and finally blocks. "
        "The try block contains risky code, except handles errors, else runs when no exception occurs, and finally runs regardless of whether an exception occurred.",

    "What is the difference between shallow copy and deep copy?":
        "A shallow copy creates a new outer object but keeps references to nested objects. "
        "A deep copy recursively copies nested objects as well, so changes to nested data in the copy do not affect the original.",

    "What are decorators in Python?":
        "Decorators are functions that modify or extend the behavior of another function without changing its original code. "
        "They are commonly used for logging, authentication, timing, validation, and other reusable functionality.",

    "How does memory management work in Python?":
        "Python manages memory automatically using a private heap and mechanisms such as reference counting and garbage collection. "
        "Objects are allocated and released automatically, which reduces the need for manual memory management by the programmer.",

    "What are generators and why are they useful?":
        "Generators are functions that produce values one at a time using the yield keyword instead of returning all values at once. "
        "They are useful for memory efficiency because they allow large or continuous sequences to be processed lazily.",

    "How would you optimize a slow Python application?":
        "I would first profile the application to identify the actual bottleneck. "
        "Then I would optimize inefficient algorithms, database queries, loops, and I/O operations, use appropriate data structures and caching, and consider asynchronous or parallel processing where suitable.",

    "What is the difference between threading and multiprocessing?":
        "Threading uses multiple threads within the same process and is useful for I/O-bound tasks. "
        "Multiprocessing uses separate processes and can execute CPU-bound work in parallel, avoiding the limitations of Python's Global Interpreter Lock for CPU-heavy tasks.",

    "How would you build a scalable Python backend?":
        "I would build a modular API using a suitable framework, use a reliable database with proper indexing, add caching, and deploy multiple application instances behind a load balancer. "
        "Monitoring, logging, asynchronous processing, security, and automated testing would also be important.",

    # -----------------------------------------------------
    # JAVA
    # -----------------------------------------------------

    "What is Java?":
        "Java is a high-level, object-oriented programming language designed to be portable across platforms through the Java Virtual Machine. "
        "It is widely used for enterprise applications, backend systems, Android development, and large-scale software.",

    "What is a class and object?":
        "A class is a blueprint that defines the properties and behaviors of a type of object. "
        "An object is an instance of a class created at runtime and contains its own state while using the behavior defined by the class.",

    "What is inheritance?":
        "Inheritance is an OOP mechanism where a child class acquires properties and methods from a parent class. "
        "It promotes code reuse and allows classes to establish an is-a relationship.",

    "What is encapsulation?":
        "Encapsulation means bundling data and the methods that operate on that data inside a class while controlling access to the internal state. "
        "Access modifiers such as private and public are commonly used to achieve this.",

    "What is polymorphism?":
        "Polymorphism means one interface or method can have multiple forms. "
        "In Java, it can be achieved through method overloading at compile time and method overriding at runtime.",

    "What is the difference between JDK, JRE and JVM?":
        "JVM is the virtual machine that executes Java bytecode. "
        "JRE provides the JVM and libraries required to run Java applications, while JDK contains the JRE plus development tools such as the compiler and debugger.",

    "What is method overloading and overriding?":
        "Method overloading means defining multiple methods with the same name but different parameter lists in the same class. "
        "Method overriding occurs when a child class provides its own implementation of a method inherited from the parent class.",

    "How does exception handling work in Java?":
        "Java uses try, catch, finally, throw, and throws for exception handling. "
        "The try block contains code that may fail, catch handles the exception, and finally is used for cleanup that should normally occur regardless of the result.",

    "What is an interface and abstract class?":
        "An interface defines a contract that implementing classes must follow, while an abstract class can contain both abstract methods and implemented methods along with shared state. "
        "Interfaces are useful for defining common behavior, while abstract classes are useful when related classes need shared implementation.",

    "How does garbage collection work in Java?":
        "Java automatically identifies objects that are no longer reachable and reclaims their memory through garbage collection. "
        "This reduces the need for manual memory deallocation, although developers still need to manage resources such as files and database connections properly.",

    "How does multithreading work in Java?":
        "Multithreading allows multiple threads to execute tasks concurrently within a Java application. "
        "Threads can be created using Thread or Runnable and are useful for responsive applications and concurrent processing, while synchronization may be required when threads share data.",

    "How would you optimize a slow Java application?":
        "I would first profile the application to identify CPU, memory, database, or I/O bottlenecks. "
        "Then I would optimize algorithms, queries, object creation, memory usage, and unnecessary operations and verify the improvement with performance testing.",

    "Explain the Java memory model.":
        "The Java memory model defines how threads interact with memory and how changes become visible between threads. "
        "It describes concepts such as heap memory, thread stacks, shared variables, synchronization, and happens-before relationships.",

    "How would you design a scalable Java backend?":
        "I would use modular services, efficient REST APIs, database indexing, caching, connection pooling, and horizontal scaling behind a load balancer. "
        "Monitoring, logging, asynchronous processing, security, and fault tolerance would also be included.",

    # -----------------------------------------------------
    # WEB
    # -----------------------------------------------------

    "What is HTML?":
        "HTML stands for HyperText Markup Language and is used to define the structure of web pages. "
        "It uses elements or tags to represent headings, paragraphs, links, images, forms, tables, and other page content.",

    "What is CSS?":
        "CSS stands for Cascading Style Sheets and is used to control the presentation of web pages. "
        "It handles properties such as colors, fonts, spacing, layouts, animations, and responsive design.",

    "What is JavaScript?":
        "JavaScript is a programming language commonly used to make web pages interactive and dynamic. "
        "It can manipulate the DOM, handle events, communicate with servers, and implement application logic in the browser and on servers using environments such as Node.js.",

    "What is a website?":
        "A website is a collection of related web pages and resources that can be accessed through the internet using a web browser. "
        "It is typically hosted on a web server and can contain HTML, CSS, JavaScript, images, APIs, and other resources.",

    "What is the difference between frontend and backend?":
        "Frontend development focuses on the user-facing part of an application, including the interface and interactions in the browser. "
        "Backend development handles server-side logic, databases, authentication, APIs, and processing behind the application.",

    "What is responsive web design?":
        "Responsive web design is an approach where a website adapts its layout and content to different screen sizes and devices. "
        "It commonly uses flexible layouts, CSS media queries, and responsive units to provide a good user experience on phones, tablets, and desktops.",

    "What is an API?":
        "API stands for Application Programming Interface. "
        "It defines a way for different software components to communicate with each other, usually through requests and responses. Web APIs commonly use HTTP methods such as GET, POST, PUT, and DELETE.",

    "What is the difference between GET and POST?":
        "GET is generally used to retrieve data from a server, while POST is generally used to send data to a server to create or process a resource. "
        "GET parameters are commonly included in the URL, whereas POST data is usually sent in the request body.",

    "What is the DOM?":
        "DOM stands for Document Object Model. "
        "It represents an HTML document as a tree of objects that JavaScript can access and modify, allowing developers to dynamically change page content, structure, and styles.",

    "What is the difference between authentication and authorization?":
        "Authentication verifies who a user is, while authorization determines what that authenticated user is allowed to access or perform. "
        "For example, logging in is authentication, while checking whether the user can access an admin page is authorization.",

    "How would you optimize a slow website?":
        "I would measure performance first using browser developer tools and performance monitoring. "
        "Then I would optimize images, CSS and JavaScript, reduce unnecessary network requests, enable caching, use compression, optimize backend and database operations, and consider a CDN.",

    "Explain how browser rendering works.":
        "The browser downloads resources such as HTML, CSS, and JavaScript, parses HTML into the DOM and CSS into the CSSOM, and combines them into a render tree. "
        "It then performs layout and painting before displaying the page on the screen.",

    "How would you design a scalable web application?":
        "I would separate frontend and backend responsibilities, design stateless APIs, use a scalable database, caching, load balancing, and horizontal application scaling. "
        "Monitoring, security, rate limiting, asynchronous processing, and fault tolerance would also be important.",

    "What are common web security vulnerabilities?":
        "Common vulnerabilities include SQL injection, cross-site scripting, broken authentication, insecure authorization, CSRF, insecure configuration, and exposure of sensitive data. "
        "Input validation, parameterized queries, secure authentication, authorization checks, HTTPS, and proper security headers help reduce these risks.",

    "How would you improve website performance?":
        "I would optimize images and static assets, reduce JavaScript and CSS overhead, minimize network requests, use browser and server-side caching, enable compression, and use a CDN when appropriate. "
        "I would also optimize backend queries and continuously measure performance.",

    # -----------------------------------------------------
    # DATA ANALYST
    # -----------------------------------------------------

    "What is data analysis?":
        "Data analysis is the process of collecting, cleaning, transforming, exploring, and interpreting data to identify useful patterns and insights. "
        "It helps organizations make informed decisions based on evidence rather than assumptions.",

    "What are mean and median?":
        "The mean is the arithmetic average calculated by adding all values and dividing by the number of values. "
        "The median is the middle value when the data is arranged in order. The median is generally less affected by extreme outliers than the mean.",

    "What is data visualization?":
        "Data visualization is the graphical representation of data using charts, graphs, dashboards, and other visual methods. "
        "It helps users identify trends, patterns, comparisons, and outliers more easily.",

    "Explain mean, median and mode.":
        "Mean is the arithmetic average of the values. Median is the middle value after sorting the data, while mode is the value that occurs most frequently. "
        "The appropriate measure depends on the type and distribution of the data.",

    "How do you handle missing data?":
        "I first identify the amount and pattern of missing data and understand why the values are missing. "
        "Depending on the situation, I may remove rows or columns, fill values using mean, median, mode, interpolation, or a suitable model, and then validate the result.",

    "Explain SQL joins.":
        "SQL joins combine rows from multiple tables using related columns. "
        "An INNER JOIN returns matching records, a LEFT JOIN keeps all records from the left table, and a RIGHT JOIN keeps all records from the right table. Joins are useful for combining related information stored in different tables.",

    "Which Python libraries are commonly used for data analysis?":
        "Common Python libraries include NumPy for numerical operations, pandas for data manipulation, Matplotlib and Seaborn for visualization, and SciPy for scientific computing. "
        "Depending on the task, libraries such as scikit-learn may also be used for machine learning.",

    "What is the difference between correlation and causation?":
        "Correlation means two variables are statistically associated or change together. "
        "Causation means a change in one variable directly produces a change in another. Correlation alone does not prove that one variable causes the other.",

    "How would you analyze a dataset containing millions of rows?":
        "I would first understand the business question and data structure, then inspect data quality and choose efficient tools and formats. "
        "I would use database-side filtering and aggregation where possible, efficient pandas operations or distributed processing when necessary, and avoid loading unnecessary data into memory.",

    "How do you handle outliers?":
        "I first identify outliers using statistical methods, visualizations, or domain knowledge and determine whether they are errors or legitimate observations. "
        "Depending on the situation, I may retain, transform, cap, or remove them, while documenting the decision.",

    "How would you explain a complex analysis to a non-technical person?":
        "I would focus on the business question and explain the result using simple language and relevant examples instead of technical jargon. "
        "I would use clear visualizations and explain what the result means, why it matters, and what action can be taken from it.",

    "How would you validate a dataset?":
        "I would check data types, missing values, duplicates, invalid ranges, inconsistent categories, unexpected values, and relationships between fields. "
        "I would compare important statistics with trusted sources or business rules and document any cleaning or validation steps.",

    "How would you design an effective dashboard?":
        "I would first identify the target users and the decisions they need to make. "
        "Then I would select relevant KPIs, use clear charts, provide filters where useful, maintain consistent formatting, and avoid unnecessary visual clutter.",

    # -----------------------------------------------------
    # AI / ML
    # -----------------------------------------------------

    "What is Artificial Intelligence?":
        "Artificial Intelligence is a field of computer science focused on creating systems that can perform tasks that normally require human-like intelligence. "
        "Examples include learning, reasoning, language processing, computer vision, and decision-making.",

    "What is Machine Learning?":
        "Machine Learning is a branch of AI where systems learn patterns from data and use those patterns to make predictions or decisions. "
        "Instead of explicitly programming every rule, a model learns from examples during training.",

    "What is supervised learning?":
        "Supervised learning is a machine learning approach where a model is trained using labeled data containing inputs and known outputs. "
        "The model learns the relationship between them and can then predict outputs for new inputs.",

    "What is a dataset?":
        "A dataset is a structured collection of data used for analysis or machine learning. "
        "It may contain rows representing observations and columns representing features or attributes.",

    "What is a feature?":
        "A feature is an input variable or measurable characteristic used by a machine learning model to make predictions. "
        "For example, in a house-price model, area, number of rooms, and location could be features.",

    "What is the difference between supervised and unsupervised learning?":
        "Supervised learning uses labeled data where the desired output is known, while unsupervised learning works with unlabeled data to discover patterns or structures. "
        "Classification and regression are supervised tasks, while clustering is a common unsupervised task.",

    "What is overfitting?":
        "Overfitting occurs when a machine learning model learns the training data too closely, including noise, and performs poorly on unseen data. "
        "It can be reduced using techniques such as regularization, cross-validation, simpler models, and more training data.",

    "What is underfitting?":
        "Underfitting occurs when a model is too simple to capture important patterns in the data. "
        "It can result in poor performance on both training and test data and may be addressed using a more suitable model, better features, or reduced regularization.",

    "What is the difference between classification and regression?":
        "Classification predicts discrete categories or classes, such as spam or not spam. "
        "Regression predicts continuous numerical values, such as house prices or temperature.",

    "Why do we split data into training and testing sets?":
        "We split data so that the model can be trained on one portion and evaluated on unseen data. "
        "This helps estimate how well the model generalizes beyond the examples it saw during training.",

    "How would you handle an imbalanced dataset?":
        "I would first measure the class imbalance and choose evaluation metrics such as precision, recall, F1-score, or ROC-AUC rather than relying only on accuracy. "
        "Depending on the problem, I might use class weighting, oversampling, undersampling, or suitable synthetic-data techniques.",

    "Explain the bias-variance tradeoff.":
        "Bias represents error caused by overly simple assumptions, while variance represents sensitivity to the training data. "
        "A good model balances both so that it is neither too simple nor excessively fitted to the training data.",

    "What would you do if your model performs poorly during validation?":
        "I would first investigate data quality, feature quality, preprocessing, class balance, and the possibility of overfitting or underfitting. "
        "Then I would compare models, tune hyperparameters, improve features, use cross-validation, and verify that the validation process is reliable.",

    "How would you deploy a machine learning model?":
        "I would save the trained model and create a service or API that accepts input data and returns predictions. "
        "I would containerize and deploy it using an appropriate platform, add validation, logging, monitoring, versioning, and a safe process for updating the model.",

    "How would you monitor a machine learning model in production?":
        "I would monitor prediction quality, latency, errors, input-data drift, output distributions, and resource usage. "
        "When ground-truth labels become available, I would also track model performance and establish alerts for significant degradation or drift.",

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    "What is a primary key?":
        "A primary key is a column or combination of columns that uniquely identifies each row in a table. "
        "It cannot contain duplicate values and normally cannot contain NULL values.",

    "What is a foreign key?":
        "A foreign key is a column or set of columns that references a key in another table. "
        "It establishes a relationship between tables and helps maintain referential integrity.",

    "What is a table?":
        "A table is a database structure that stores related data in rows and columns. "
        "Columns define the attributes or fields, while each row represents a record.",

    "What is normalization?":
        "Normalization is the process of organizing relational database tables to reduce data redundancy and improve data integrity. "
        "It commonly involves dividing data into related tables and defining appropriate relationships between them.",

    "What is a database index?":
        "A database index is a data structure that helps the database find rows more efficiently during search and query operations. "
        "Indexes can improve read performance but require additional storage and can add overhead to insert and update operations.",

    "What is the difference between DELETE, DROP and TRUNCATE?":
        "DELETE removes selected rows and can use a WHERE condition. TRUNCATE removes all rows from a table with less logging in many database systems. "
        "DROP removes the table itself, including its structure. The exact transaction behavior can vary by database system.",

    "What is a database transaction?":
        "A transaction is a logical unit of database operations that should be completed reliably as a group. "
        "Transactions commonly use properties described by ACID: atomicity, consistency, isolation, and durability. COMMIT saves changes and ROLLBACK reverses uncommitted changes.",

    "How would you optimize a slow SQL query?":
        "I would inspect the execution plan to identify expensive operations such as full table scans, inefficient joins, or sorting. "
        "Then I would optimize the query, add appropriate indexes, avoid unnecessary columns, improve joins and filtering, and verify the result using execution statistics.",

    "How does indexing affect database performance?":
        "Indexes can make SELECT queries faster by allowing the database to locate rows without scanning the entire table. "
        "However, indexes consume storage and can slow INSERT, UPDATE, and DELETE operations because the index also needs to be maintained.",

    "How would you design a database for a large application?":
        "I would first identify entities, relationships, access patterns, and consistency requirements. "
        "I would design normalized tables where appropriate, define keys and constraints, add indexes based on query patterns, and consider replication, partitioning, caching, and scaling requirements.",

    "What is database sharding?":
        "Database sharding is a horizontal scaling technique where data is distributed across multiple database servers or shards. "
        "Each shard stores a portion of the data, allowing large datasets and high traffic to be distributed across multiple machines.",

    "How would you design a scalable database?":
        "I would begin with an efficient schema and appropriate indexes based on expected queries. "
        "For higher scale, I would consider read replicas, partitioning, caching, connection pooling, replication, and eventually sharding when a single database cannot handle the workload.",

    # -----------------------------------------------------
    # HR
    # -----------------------------------------------------

    "Tell me about yourself.":
        "I am a motivated IT student with an interest in software development and problem solving. "
        "I am building my skills in programming, databases, web technologies, and data structures and algorithms. "
        "I also work on practical projects to apply what I learn, and my goal is to start my career in a role where I can contribute, learn from experienced professionals, and continuously improve my technical and communication skills.",

    "Why did you choose IT?":
        "I chose IT because I enjoy technology, problem solving, and building things using software. "
        "I like the fact that IT provides continuous learning opportunities and allows me to work on practical solutions that can solve real-world problems.",

    "What are your strengths?":
        "My strengths are willingness to learn, consistency, problem solving, and the ability to adapt to new technologies. "
        "I also try to take feedback positively and use it to improve my performance.",

    "What are your hobbies?":
        "My hobbies include learning new technology, listening to music, and spending time on activities that help me relax and stay creative. "
        "I also enjoy exploring new topics and improving my skills outside regular academic work.",

    "Why should we hire you?":
        "You should consider me because I am willing to learn, have a strong interest in technology, and actively work on improving my technical and communication skills. "
        "As a fresher, I may not know everything yet, but I am adaptable, hardworking, and ready to learn quickly and contribute to the team.",

    "Tell me about a challenging project.":
        "One challenging project can be described by explaining the problem, my role, the technical approach, and the result. "
        "I would focus on a situation where I faced a technical or coordination challenge, researched possible solutions, implemented one, tested it, and learned something useful from the experience.",

    "How do you handle pressure?":
        "I handle pressure by breaking the work into smaller tasks and prioritizing what needs to be completed first. "
        "I try to remain calm, communicate early if there is a problem, and focus on solving the issue instead of spending time worrying about it.",

    "How do you work in a team?":
        "I believe effective teamwork requires clear communication, responsibility, and respect for other people's ideas. "
        "I try to complete my assigned work on time, communicate blockers early, help teammates when possible, and remain open to feedback.",

    "What is your weakness?":
        "One area I am working on is becoming more confident while communicating in unfamiliar situations. "
        "I am improving it through presentations, mock interviews, speaking practice, and deliberately putting myself in situations where I need to communicate clearly.",

    "Why should we select you over another candidate?":
        "I would not compare myself negatively or positively with another candidate without knowing their strengths. "
        "What I can offer is a strong willingness to learn, consistent effort, adaptability, and a genuine interest in the role. I would focus on demonstrating these qualities through my work and performance.",

    "Tell me about a failure and what you learned from it.":
        "A good example would be a situation where I initially underestimated the time or complexity of a task. "
        "I learned the importance of planning, breaking work into smaller milestones, testing earlier, and communicating problems instead of waiting until the deadline.",

    "How would you handle a disagreement with a teammate?":
        "I would first listen to the teammate's reasoning and explain my own perspective calmly. "
        "I would compare both approaches using project requirements and evidence rather than making the discussion personal. If needed, I would involve a senior or mentor to reach a practical decision.",

    "Where do you see yourself in five years?":
        "In five years, I want to be a strong software professional with solid technical skills and meaningful project experience. "
        "I would like to take greater responsibility, contribute to important projects, continue learning new technologies, and gradually develop leadership skills.",

    "Why did you choose Python?":
        "I chose Python because it has readable syntax, a large ecosystem, and applications across web development, automation, data analysis, and AI. "
        "It is also beginner-friendly while still being powerful enough for real-world projects.",

    "What is your most important project?":
        "My most important project is one where I had to combine multiple technical concepts and solve a practical problem. "
        "I would explain the project's objective, my specific contribution, the technologies used, the challenges I faced, and what I learned from building it.",

    "How do you handle deadlines?":
        "I handle deadlines by understanding the required outcome, breaking the task into smaller milestones, and prioritizing the most important work first. "
        "I also track progress regularly and communicate early if I identify a risk to the deadline.",

    "Tell me about a failure.":
        "A failure is useful when it leads to a clear lesson. "
        "For example, if I failed to complete a task as planned, I would identify the reason, understand what I could control, improve my planning, and apply that lesson to future tasks.",

    "Why should we hire you as a Python developer?":
        "I have a genuine interest in Python and am continuously building my understanding of programming, problem solving, and Python-based development. "
        "I am willing to learn the technologies used by the team and can contribute through consistent effort, adaptability, and a strong learning mindset.",

    "Why did you choose Java?":
        "I chose Java because it is widely used in enterprise and backend development and provides strong object-oriented programming concepts. "
        "Learning Java also helps build a solid understanding of structured software development and scalable applications.",

    "Why should we hire you as a Java developer?":
        "I am interested in Java development and understand the importance of object-oriented programming, clean code, and problem solving. "
        "As a fresher, I am ready to learn the team's technologies and contribute through consistent practice, adaptability, and disciplined development.",

    "Why did you choose web development?":
        "I chose web development because it allows me to build applications that users can directly interact with. "
        "I enjoy understanding both the visual side of an application and the programming and backend logic behind it.",

    "Why should we select you as a web developer?":
        "I have an interest in building web applications and continuously improving my understanding of HTML, CSS, JavaScript, APIs, and backend concepts. "
        "I am adaptable, willing to learn, and ready to improve my skills through practical project work.",

    "Why did you choose data analytics?":
        "I chose data analytics because I enjoy working with data and finding patterns that can support better decisions. "
        "It combines programming, statistics, problem solving, and visualization, which makes it an interesting field for me.",

    "Why should we select you as a data analyst?":
        "I am interested in data analysis and am building skills in SQL, Python, statistics, data cleaning, and visualization. "
        "I am comfortable learning new tools and would focus on producing accurate analysis and communicating insights clearly.",

    "Why did you choose AI and ML?":
        "I chose AI and ML because I am interested in how data and algorithms can be used to create systems that learn and make predictions. "
        "The field also offers continuous opportunities to learn mathematics, programming, and practical problem solving.",

    "Why should we select you as an AI/ML engineer?":
        "I have a strong interest in artificial intelligence and machine learning and am developing my understanding of programming, data, and machine learning concepts. "
        "I am willing to strengthen my technical foundation continuously and apply what I learn through practical projects.",

    "Why did you choose database development?":
        "I chose database development because reliable data storage and retrieval are fundamental to almost every software application. "
        "I am interested in SQL, database design, normalization, performance, and understanding how applications interact with data.",

    "Why should we select you as a database developer?":
        "I am interested in SQL and database concepts such as keys, relationships, normalization, queries, and performance. "
        "I am also willing to continuously improve my database skills and learn the tools and systems used by the organization.",

    "Why should we select you as a web developer?":
        "I am interested in web development and enjoy understanding how frontend interfaces communicate with backend services. "
        "I am building practical skills in HTML, CSS, JavaScript, APIs, and application development and am ready to keep learning.",

    "Why should we select you as a data analyst?":
        "I am developing skills in SQL, Python, statistics, data cleaning, and visualization. "
        "I enjoy working with data and explaining insights clearly, and I am willing to learn the organization's tools and business domain.",

    "Why should we select you as an AI/ML engineer?":
        "I have a strong interest in AI and machine learning and am building my foundation in programming, data handling, and machine learning concepts. "
        "I am comfortable learning continuously and applying concepts through practical projects.",

    "Why should we select you as a database developer?":
        "I am interested in database systems, SQL, data modeling, and query optimization. "
        "I am building my technical foundation and would bring a learning mindset, consistency, and willingness to improve with practical experience."
}


# =========================================================
# BEST FITTING ANSWER FUNCTION
# =========================================================

def get_best_fitting_answer(question):
    """
    Returns the ideal/model answer for the exact question.
    If an exact answer is not found, a safe question-specific
    fallback is returned.
    """

    answer = BEST_FITTING_ANSWERS.get(question)

    if answer:
        return answer

    # Additional generic fallbacks for repeated HR questions
    if question.startswith("Why should we hire you"):
        return (
            "I believe I would be a good candidate because I am willing to learn, "
            "adaptable, and genuinely interested in the role. I would focus on "
            "building the required technical skills, taking feedback positively, "
            "and contributing consistently to the team."
        )

    if question.startswith("Where do you see yourself"):
        return (
            "In five years, I would like to have strong technical expertise, "
            "solid project experience, and greater responsibility in my organization. "
            "I also want to continue learning and gradually develop leadership skills."
        )

    if question.startswith("Tell me about a failure"):
        return (
            "I would describe a genuine situation where something did not go as planned, "
            "explain what caused the problem, what I did to fix it, and most importantly "
            "what I learned and changed afterward."
        )

    if question.startswith("Tell me about a challenging project"):
        return (
            "I would explain the project's objective, my specific responsibility, "
            "the main challenge, the approach I used to solve it, and the final result. "
            "I would also mention what I learned from the experience."
        )

    return (
        "A strong answer should directly define the concept, explain its main purpose "
        "or working, and provide a relevant example or practical use case where appropriate."
    )


# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {

    "started": False,
    "finished": False,

    "current_question": 0,
    "questions": [],
    "answers": [],

    "scores": [],
    "relevance_scores": [],
    "communication_scores": [],
    "completeness_scores": [],
    "keyword_counts": [],

    "resume_text": "",
    "resume_name": "",

    "role": "",
    "difficulty": "",
    "interview_type": "",

    "question_history": [],

    "visual_history": [],
    "question_visual_history": {},
    "continuous_visual_result": None,

    "answer_metrics": [],
    "filler_word_counts": [],
    "speech_word_counts": [],
    "answer_durations": [],
    "words_per_minute": [],
    "fluency_scores": [],
    "confidence_indicators": [],
    "nervousness_indicators": [],

    "current_annotated_frame": None,

    "interview_start_time": None,
    "last_processed_audio_hash": {}
}


for key, value in DEFAULTS.items():

    if key not in st.session_state:

        if isinstance(value, list):
            st.session_state[key] = []

        elif isinstance(value, dict):
            st.session_state[key] = {}

        else:
            st.session_state[key] = value


# =========================================================
# RESET
# =========================================================

def reset_interview():

    for key, value in DEFAULTS.items():

        if isinstance(value, list):
            st.session_state[key] = []

        elif isinstance(value, dict):
            st.session_state[key] = {}

        else:
            st.session_state[key] = value


# =========================================================
# RESUME EXTRACTION
# =========================================================

def extract_resume_text(uploaded_file):

    if uploaded_file is None:
        return ""

    try:

        filename = uploaded_file.name.lower()

        if filename.endswith(".pdf"):

            reader = PdfReader(uploaded_file)

            text = ""

            for page in reader.pages:

                page_text = page.extract_text() or ""

                text += page_text + "\n"

            return text.strip()

        elif filename.endswith(".docx"):

            document = Document(uploaded_file)

            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            ).strip()

        elif filename.endswith(".txt"):

            return uploaded_file.read().decode(
                "utf-8",
                errors="ignore"
            )

        return ""

    except Exception as e:

        st.error(f"Could not read resume: {e}")

        return ""


# =========================================================
# QUESTION SPEECH
# =========================================================

def speak_question(text):

    safe_text = (
        text
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", " ")
    )

    st.components.v1.html(
        f"""
        <script>
        const msg = new SpeechSynthesisUtterance('{safe_text}');
        msg.rate = 0.9;
        msg.pitch = 1;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
        </script>
        """,
        height=0
    )


# =========================================================
# FACE DETECTOR
# =========================================================

if os.path.exists(HAAR_CASCADE_PATH):

    face_detector = cv2.CascadeClassifier(
        HAAR_CASCADE_PATH
    )

else:

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )


# =========================================================
# FACE / VISUAL ANALYSIS
# =========================================================

def analyze_visual_snapshot(image_bytes):

    try:

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return None, None

        height, width = frame.shape[:2]

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        result = {
            "timestamp": time.time(),
            "face_detected": False,
            "face_count": len(faces),
            "expression": "Unknown",
            "framing_score": 0,
            "face_position": "Not detected",
            "vertical_position": "Not detected",
            "face_size_percent": 0
        }

        annotated = frame.copy()

        if len(faces) == 0:

            result["framing_score"] = 0

            cv2.putText(
                annotated,
                "No face detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

            return result, annotated

        x, y, w, h = max(
            faces,
            key=lambda rect: rect[2] * rect[3]
        )

        result["face_detected"] = True

        center_x = x + w / 2
        center_y = y + h / 2

        horizontal_error = abs(
            center_x - width / 2
        ) / (width / 2)

        vertical_error = abs(
            center_y - height / 2
        ) / (height / 2)

        horizontal_score = max(
            0,
            100 - horizontal_error * 100
        )

        vertical_score = max(
            0,
            100 - vertical_error * 100
        )

        framing_score = (
            horizontal_score * 0.55 +
            vertical_score * 0.45
        )

        face_area = w * h

        face_size_percent = (
            face_area /
            (width * height)
        ) * 100

        if face_size_percent < 3:
            framing_score -= 20

        elif face_size_percent < 6:
            framing_score -= 8

        framing_score = max(
            0,
            min(100, framing_score)
        )

        result["framing_score"] = round(
            framing_score,
            1
        )

        result["face_size_percent"] = round(
            face_size_percent,
            2
        )

        if center_x < width * 0.4:

            result["face_position"] = "Left"

        elif center_x > width * 0.6:

            result["face_position"] = "Right"

        else:

            result["face_position"] = "Center"

        if center_y < height * 0.4:

            result["vertical_position"] = "High"

        elif center_y > height * 0.65:

            result["vertical_position"] = "Low"

        else:

            result["vertical_position"] = "Good"

        cv2.rectangle(
            annotated,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        try:

            analysis = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="opencv"
            )

            if isinstance(analysis, list):
                analysis = analysis[0]

            emotion_scores = analysis.get(
                "emotion",
                {}
            )

            if emotion_scores:

                expression = max(
                    emotion_scores,
                    key=emotion_scores.get
                )

                result["expression"] = expression.title()

        except Exception:

            result["expression"] = "Unknown"

        cv2.putText(
            annotated,
            f"Expression: {result['expression']}",
            (x, max(30, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 0),
            2
        )

        cv2.putText(
            annotated,
            f"Framing: {result['framing_score']:.1f}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        return result, annotated

    except Exception:

        return None, None


# =========================================================
# VISUAL SUMMARY
# =========================================================

def calculate_visual_summary(results):

    if not results:

        return {
            "samples": 0,
            "avg_framing": 0,
            "face_visibility": 0,
            "dominant_expression": "Unknown",
            "expressions": {}
        }

    valid = [
        r
        for r in results
        if r is not None
    ]

    if not valid:

        return {
            "samples": 0,
            "avg_framing": 0,
            "face_visibility": 0,
            "dominant_expression": "Unknown",
            "expressions": {}
        }

    avg_framing = np.mean([
        r.get("framing_score", 0)
        for r in valid
    ])

    face_visibility = (
        sum(
            1
            for r in valid
            if r.get("face_detected", False)
        )
        /
        len(valid)
    ) * 100

    expressions = Counter()

    for r in valid:

        expression = r.get(
            "expression",
            "Unknown"
        )

        if expression != "Unknown":

            expressions[expression] += 1

    dominant = (
        expressions.most_common(1)[0][0]
        if expressions
        else "Unknown"
    )

    return {
        "samples": len(valid),
        "avg_framing": round(
            float(avg_framing),
            1
        ),
        "face_visibility": round(
            float(face_visibility),
            1
        ),
        "dominant_expression": dominant,
        "expressions": dict(expressions)
    }


# =========================================================
# FILLER COUNT
# =========================================================

def count_filler_words(answer):

    lower = " ".join(
        answer.lower().split()
    )

    count = 0

    for filler in FILLER_WORDS:

        pattern = (
            r"\b" +
            re.escape(filler) +
            r"\b"
        )

        count += len(
            re.findall(
                pattern,
                lower
            )
        )

    return count


# =========================================================
# FLUENCY
# =========================================================

def calculate_fluency(word_count, duration):

    if duration <= 0:
        return 5.0

    wpm = word_count / (
        duration / 60
    )

    if 110 <= wpm <= 160:
        score = 10.0

    elif 90 <= wpm <= 180:
        score = 8.0

    elif 70 <= wpm <= 200:
        score = 6.0

    elif 50 <= wpm <= 220:
        score = 5.0

    else:
        score = 3.0

    return score


# =========================================================
# ANSWER ANALYSIS
# =========================================================

def analyze_answer(question, answer):

    clean_answer = " ".join(
        answer.strip().split()
    )

    words = clean_answer.split()

    word_count = len(words)

    lower_answer = clean_answer.lower()

    keywords = QUESTION_KEYWORDS.get(
        question,
        []
    )

    matched = []

    for keyword in keywords:

        if keyword.lower() in lower_answer:

            matched.append(keyword)

    keyword_count = len(
        set(matched)
    )

    if keywords:

        relevance = (
            keyword_count /
            len(keywords)
        ) * 10

    else:

        relevance = 6.0

    relevance = max(
        0,
        min(10, relevance)
    )

    if word_count >= 80:

        communication = 10

    elif word_count >= 50:

        communication = 9

    elif word_count >= 30:

        communication = 8

    elif word_count >= 20:

        communication = 7

    elif word_count >= 10:

        communication = 5

    elif word_count >= 5:

        communication = 4

    else:

        communication = 2

    if word_count >= 100:

        completeness = 10

    elif word_count >= 70:

        completeness = 9

    elif word_count >= 45:

        completeness = 8

    elif word_count >= 30:

        completeness = 7

    elif word_count >= 20:

        completeness = 6

    elif word_count >= 10:

        completeness = 4

    else:

        completeness = 2

    overall = (
        relevance * 0.45 +
        communication * 0.25 +
        completeness * 0.30
    )

    return {
        "overall": round(
            overall,
            1
        ),
        "relevance": round(
            relevance,
            1
        ),
        "communication": round(
            communication,
            1
        ),
        "completeness": round(
            completeness,
            1
        ),
        "keyword_count": keyword_count,
        "matched_keywords": matched,
        "word_count": word_count
    }


# =========================================================
# CONFIDENCE INDICATOR
# =========================================================

def calculate_confidence(
    answer_data,
    fluency,
    framing
):

    value = (

        answer_data["overall"] * 10 * 0.35 +

        answer_data["relevance"] * 10 * 0.10 +

        answer_data["communication"] * 10 * 0.20 +

        answer_data["completeness"] * 10 * 0.15 +

        fluency * 10 * 0.10 +

        framing * 0.10

    )

    return round(
        max(0, min(100, value)),
        1
    )


# =========================================================
# NERVOUSNESS INDICATOR
# =========================================================

def calculate_nervousness(
    filler_density,
    fluency,
    word_count,
    communication,
    framing,
    face_detected
):

    score = 0

    if filler_density > 8:
        score += 30

    elif filler_density > 5:
        score += 20

    elif filler_density > 2:
        score += 10

    if fluency < 6:
        score += 20

    if word_count < 15:
        score += 15

    if communication <= 5:
        score += 15

    if framing < 70:
        score += 10

    if not face_detected:
        score += 10

    return round(
        min(100, score),
        1
    )


# =========================================================
# FEEDBACK
# =========================================================

def get_feedback(
    question,
    answer_data,
    filler_count,
    wpm,
    fluency,
    confidence,
    nervousness
):

    feedback = []

    if answer_data["relevance"] < 6:

        feedback.append(
            "Focus more directly on the concepts asked in the question."
        )

    elif answer_data["relevance"] < 8:

        feedback.append(
            "Your answer is relevant, but include more important technical concepts."
        )

    else:

        feedback.append(
            "Your answer stayed relevant to the question."
        )

    if answer_data["completeness"] < 6:

        feedback.append(
            "Add a definition, explanation and a simple example."
        )

    elif answer_data["completeness"] < 8:

        feedback.append(
            "Add one or two supporting points or examples."
        )

    if answer_data["communication"] < 6:

        feedback.append(
            "Try giving a slightly longer and more structured answer."
        )

    if filler_count > 5:

        feedback.append(
            "Reduce filler words such as 'um', 'uh', 'like' and 'basically'."
        )

    if wpm > 180:

        feedback.append(
            "Your speaking pace appears fast. Slow down slightly."
        )

    elif 0 < wpm < 70:

        feedback.append(
            "Try to maintain a more natural speaking pace."
        )

    if fluency < 6:

        feedback.append(
            "Practice speaking answers aloud before interviews."
        )

    if confidence < 60:

        feedback.append(
            "Use a clear structure: definition → explanation → example."
        )

    if nervousness > 50:

        feedback.append(
            "Take a short pause before answering and organize your thoughts."
        )

    return feedback


# =========================================================
# SMART IMPROVEMENT AREAS
# =========================================================

def get_improvement_areas(
    avg_communication,
    avg_completeness,
    avg_relevance,
    avg_fluency,
    avg_confidence,
    avg_nervousness,
    avg_wpm,
    avg_filler,
    visual_summary
):

    improvements = []

    if avg_communication < 6:

        improvements.append(
            "Communication needs improvement: give longer, clearer and better-structured answers."
        )

    elif avg_communication < 7.5:

        improvements.append(
            "Communication can be improved by using clearer sentence structure and smoother explanations."
        )

    if avg_completeness < 6:

        improvements.append(
            "Answer completeness is low: use a Definition → Explanation → Example structure."
        )

    elif avg_completeness < 7.5:

        improvements.append(
            "Add supporting points and practical examples to make answers more complete."
        )

    if avg_relevance < 6:

        improvements.append(
            "Technical relevance needs improvement: revise core concepts and answer the exact question asked."
        )

    elif avg_relevance < 7.5:

        improvements.append(
            "Strengthen technical knowledge and include more question-specific concepts in your answers."
        )

    if avg_fluency < 6:

        improvements.append(
            "Fluency needs practice: speak answers aloud regularly and focus on smooth delivery."
        )

    elif avg_fluency < 7.5:

        improvements.append(
            "Work on speaking smoothly with fewer pauses and interruptions."
        )

    if avg_confidence < 60:

        improvements.append(
            "Confidence indicator is low: pause briefly, organize your thoughts and use a structured answer."
        )

    elif avg_confidence < 70:

        improvements.append(
            "Build interview confidence through repeated mock interviews and structured practice."
        )

    if avg_nervousness > 50:

        improvements.append(
            "The interview behaviour indicators suggest frequent signs associated with nervous delivery; practice timed mock interviews and controlled pauses."
        )

    elif avg_nervousness > 35:

        improvements.append(
            "Work on interview composure by slowing down, pausing before answers and practicing under time pressure."
        )

    if avg_wpm > 180:

        improvements.append(
            "Speaking pace is relatively fast; slow down slightly so answers remain easy to follow."
        )

    elif 0 < avg_wpm < 70:

        improvements.append(
            "Speaking pace is relatively slow; practice maintaining a more natural conversational pace."
        )

    if avg_filler >= 6:

        improvements.append(
            "Reduce filler words such as 'um', 'uh', 'like' and 'basically' by pausing silently instead."
        )

    elif avg_filler >= 3:

        improvements.append(
            "Try to reduce filler words and replace them with short natural pauses."
        )

    if visual_summary["samples"] > 0:

        if visual_summary["face_visibility"] < 75:

            improvements.append(
                "Improve camera positioning and keep your face visible throughout the interview."
            )

        elif visual_summary["avg_framing"] < 75:

            improvements.append(
                "Improve camera framing by keeping your face centered and appropriately positioned."
            )

    if not improvements:

        improvements.append(
            "Performance is reasonably balanced. Continue practicing with progressively harder interview questions."
        )

    unique_improvements = []

    for item in improvements:

        if item not in unique_improvements:

            unique_improvements.append(item)

    return unique_improvements


# =========================================================
# FINAL SUMMARY
# =========================================================

def get_final_summary(
    avg_score,
    avg_relevance,
    avg_communication,
    avg_completeness,
    avg_fluency,
    avg_confidence,
    avg_nervousness,
    avg_wpm,
    avg_filler,
    visual_summary
):

    strengths = []
    focus = []

    if avg_relevance >= 7.5:
        strengths.append("Good question relevance")

    if avg_communication >= 7.5:
        strengths.append("Good communication")

    if avg_completeness >= 7.5:
        strengths.append("Reasonably complete answers")

    if avg_fluency >= 7.5:
        strengths.append("Good speaking fluency")

    if avg_confidence >= 70:
        strengths.append("Good confidence indicator")

    if visual_summary["samples"] > 0:

        if visual_summary["avg_framing"] >= 80:
            strengths.append("Good camera framing")

        if visual_summary["face_visibility"] >= 85:
            strengths.append("Good face visibility")

    if not strengths:

        strengths.append(
            "The interview provides a useful baseline for further practice."
        )

    if avg_relevance < 7:
        focus.append("technical relevance")

    if avg_communication < 7:
        focus.append("communication")

    if avg_completeness < 7:
        focus.append("answer completeness")

    if avg_fluency < 7:
        focus.append("fluency")

    if avg_confidence < 70:
        focus.append("confidence")

    if avg_nervousness > 40:
        focus.append("interview composure")

    if avg_wpm > 180:
        focus.append("speaking pace")

    elif 0 < avg_wpm < 70:
        focus.append("speaking pace")

    if avg_filler >= 3:
        focus.append("filler-word reduction")

    if not focus:
        focus.append("maintaining consistency")

    if avg_score >= 8:

        performance = (
            "The interview performance was strong overall, "
            "with generally effective answers and interview delivery."
        )

    elif avg_score >= 6:

        performance = (
            "The interview performance was moderate overall. "
            "The candidate demonstrated a useful foundation, "
            "but several areas can be improved through targeted practice."
        )

    else:

        performance = (
            "The interview performance indicates that more preparation "
            "and structured practice would be beneficial before a real interview."
        )

    return {
        "performance": performance,
        "strengths": strengths,
        "focus": focus
    }


# =========================================================
# VIDEO PROCESSOR
# =========================================================

class InterviewVideoProcessor:

    def __init__(self):

        self.latest_frame = None
        self.latest_timestamp = 0.0

    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        self.latest_frame = img.copy()

        self.latest_timestamp = time.time()

        return frame


# =========================================================
# PDF PAGE NUMBER
# =========================================================

def add_page_number(canvas, doc):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.drawCentredString(
        A4[0] / 2,
        18,
        f"AI Mock Interview Report • Page {doc.page}"
    )

    canvas.restoreState()


# =========================================================
# PDF REPORT
# =========================================================

def build_pdf_report():

    if not REPORTLAB_AVAILABLE:
        return None

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=42,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=27,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey,
        leading=14,
        spaceAfter=5
    )

    heading_style = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=15,
        leading=19,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor("#243b53")
    )

    subheading_style = ParagraphStyle(
        "SubHeadingCustom",
        parent=styles["Heading3"],
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=4
    )

    small_style = ParagraphStyle(
        "SmallCustom",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555")
    )

    your_answer_style = ParagraphStyle(
        "YourAnswerStyle",
        parent=body_style,
        fontSize=9,
        leading=13,
        backColor=colors.HexColor("#f8fafc"),
        borderColor=colors.HexColor("#dbeafe"),
        borderWidth=0.5,
        borderPadding=8,
        spaceAfter=8
    )

    best_answer_style = ParagraphStyle(
        "BestAnswerStyle",
        parent=body_style,
        fontSize=9,
        leading=13,
        backColor=colors.HexColor("#f0fdf4"),
        borderColor=colors.HexColor("#bbf7d0"),
        borderWidth=0.5,
        borderPadding=8,
        spaceAfter=10
    )

    story = []

    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    scores = st.session_state.scores
    relevance = st.session_state.relevance_scores
    communication = st.session_state.communication_scores
    completeness = st.session_state.completeness_scores
    fluency = st.session_state.fluency_scores
    confidence = st.session_state.confidence_indicators
    nervousness = st.session_state.nervousness_indicators

    def avg(values):

        return (
            round(
                float(np.mean(values)),
                1
            )
            if values
            else 0
        )

    avg_overall = avg(scores)
    avg_relevance = avg(relevance)
    avg_communication = avg(communication)
    avg_completeness = avg(completeness)
    avg_fluency = avg(fluency)
    avg_confidence = avg(confidence)
    avg_nervousness = avg(nervousness)

    avg_wpm = avg(
        st.session_state.words_per_minute
    )

    avg_filler = avg(
        st.session_state.filler_word_counts
    )

    visual_summary = calculate_visual_summary(
        st.session_state.visual_history
    )

    improvements = get_improvement_areas(
        avg_communication,
        avg_completeness,
        avg_relevance,
        avg_fluency,
        avg_confidence,
        avg_nervousness,
        avg_wpm,
        avg_filler,
        visual_summary
    )

    final_summary = get_final_summary(
        avg_overall,
        avg_relevance,
        avg_communication,
        avg_completeness,
        avg_fluency,
        avg_confidence,
        avg_nervousness,
        avg_wpm,
        avg_filler,
        visual_summary
    )

    # -----------------------------------------------------
    # COVER
    # -----------------------------------------------------

    story.append(Spacer(1, 35))

    story.append(
        Paragraph(
            "AI Mock Interview",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Comprehensive Interview Performance Report",
            ParagraphStyle(
                "ReportTitle",
                parent=subtitle_style,
                fontSize=13,
                textColor=colors.HexColor("#4f46e5"),
                spaceAfter=18
            )
        )
    )

    metadata_data = [
        ["Role", escape(str(st.session_state.role))],
        ["Interview Type", escape(str(st.session_state.interview_type))],
        ["Difficulty", escape(str(st.session_state.difficulty))],
        [
            "Date & Time",
            escape(
                datetime.now().strftime(
                    "%d %B %Y, %I:%M %p"
                )
            )
        ]
    ]

    metadata_table = Table(
        metadata_data,
        colWidths=[130, 330]
    )

    metadata_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#eef2ff")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (0, -1),
                colors.HexColor("#3730a3")
            ),
            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#d1d5db")
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(metadata_table)
    story.append(Spacer(1, 20))

    # -----------------------------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Executive Summary",
            heading_style
        )
    )

    story.append(
        Paragraph(
            escape(
                final_summary["performance"]
            ),
            body_style
        )
    )

    story.append(
        Paragraph(
            "<b>Key strengths:</b> " +
            escape(
                ", ".join(
                    final_summary["strengths"]
                )
            ),
            body_style
        )
    )

    story.append(
        Paragraph(
            "<b>Primary focus areas:</b> " +
            escape(
                ", ".join(
                    final_summary["focus"]
                )
            ),
            body_style
        )
    )

    story.append(Spacer(1, 12))

    # -----------------------------------------------------
    # OVERALL PERFORMANCE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Overall Performance",
            heading_style
        )
    )

    overview_data = [
        ["Metric", "Score"],
        ["Overall Performance", f"{avg_overall}/10"],
        ["Technical / Question Relevance", f"{avg_relevance}/10"],
        ["Communication", f"{avg_communication}/10"],
        ["Completeness", f"{avg_completeness}/10"],
        ["Fluency", f"{avg_fluency}/10"],
        ["Confidence Indicator", f"{avg_confidence}/100"],
        ["Nervousness Indicator", f"{avg_nervousness}/100"],
        ["Average Speaking Rate", f"{avg_wpm} WPM"],
        ["Average Filler Words", f"{avg_filler}"],
        [
            "Average Visual Framing",
            f"{visual_summary['avg_framing']}/100"
        ],
        [
            "Face Visibility",
            f"{visual_summary['face_visibility']}%"
        ]
    ]

    table = Table(
        overview_data,
        colWidths=[285, 175],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#4f46e5")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#d1d5db")
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f8fafc")
                ]
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(table)
    story.append(Spacer(1, 18))

    # -----------------------------------------------------
    # IMPROVEMENT AREAS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Areas to Work On",
            heading_style
        )
    )

    for index, item in enumerate(
        improvements,
        start=1
    ):

        story.append(
            Paragraph(
                f"<b>{index}.</b> " +
                escape(item),
                body_style
            )
        )

    story.append(Spacer(1, 15))

    # -----------------------------------------------------
    # VISUAL ANALYSIS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Continuous Visual Interview Analysis",
            heading_style
        )
    )

    visual_data = [
        ["Visual Metric", "Result"],
        [
            "Visual Samples",
            str(visual_summary["samples"])
        ],
        [
            "Average Framing",
            f"{visual_summary['avg_framing']}/100"
        ],
        [
            "Face Visibility",
            f"{visual_summary['face_visibility']}%"
        ],
        [
            "Dominant Expression Pattern",
            escape(
                visual_summary["dominant_expression"]
            )
        ]
    ]

    visual_table = Table(
        visual_data,
        colWidths=[285, 175],
        repeatRows=1
    )

    visual_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#4f46e5")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#d1d5db")
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f8fafc")
                ]
            )
        ])
    )

    story.append(visual_table)
    story.append(Spacer(1, 8))

    if visual_summary["expressions"]:

        expression_text = ", ".join(
            f"{key}: {value}"
            for key, value
            in visual_summary["expressions"].items()
        )

        story.append(
            Paragraph(
                "<b>Expression distribution:</b> " +
                escape(expression_text),
                small_style
            )
        )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            escape(
                "Visual indicators describe camera framing, face visibility "
                "and AI-estimated facial-expression patterns from sampled "
                "frames. They should not be interpreted as direct measurements "
                "of actual emotions or psychological states."
            ),
            small_style
        )
    )

    # -----------------------------------------------------
    # QUESTION-WISE PERFORMANCE
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Question-wise Performance",
            heading_style
        )
    )

    for i, question in enumerate(
        st.session_state.questions
    ):

        answer = (
            st.session_state.answers[i]
            if i < len(st.session_state.answers)
            else "No answer recorded"
        )

        data = (
            st.session_state.answer_metrics[i]
            if i < len(st.session_state.answer_metrics)
            else {}
        )

        best_answer = get_best_fitting_answer(
            question
        )

        visual = calculate_visual_summary(
            st.session_state.question_visual_history.get(
                i,
                []
            )
        )

        question_header = Paragraph(
            escape(
                f"Q{i + 1}. {question}"
            ),
            subheading_style
        )

        story.append(question_header)

        # -------------------------------------------------
        # YOUR ANSWER
        # -------------------------------------------------

        story.append(
            Paragraph(
                "<b>🎤 Your Answer</b>",
                body_style
            )
        )

        story.append(
            Paragraph(
                escape(
                    answer if answer.strip()
                    else "No answer recorded."
                ),
                your_answer_style
            )
        )

        # -------------------------------------------------
        # BEST FITTING ANSWER
        # -------------------------------------------------

        story.append(
            Paragraph(
                "<b>✅ Best Fitting Answer</b>",
                body_style
            )
        )

        story.append(
            Paragraph(
                escape(best_answer),
                best_answer_style
            )
        )

        # -------------------------------------------------
        # METRICS
        # -------------------------------------------------

        question_table = [
            ["Metric", "Value"],
            [
                "Overall",
                f"{data.get('overall', 0)}/10"
            ],
            [
                "Relevance",
                f"{data.get('relevance', 0)}/10"
            ],
            [
                "Communication",
                f"{data.get('communication', 0)}/10"
            ],
            [
                "Completeness",
                f"{data.get('completeness', 0)}/10"
            ],
            [
                "Word Count",
                str(data.get("word_count", 0))
            ],
            [
                "Filler Words",
                str(data.get("filler_count", 0))
            ],
            [
                "Speaking Rate",
                f"{data.get('wpm', 0)} WPM"
            ],
            [
                "Fluency",
                f"{data.get('fluency', 0)}/10"
            ],
            [
                "Confidence Indicator",
                f"{data.get('confidence', 0)}/100"
            ],
            [
                "Nervousness Indicator",
                f"{data.get('nervousness', 0)}/100"
            ],
            [
                "Visual Samples",
                str(visual["samples"])
            ],
            [
                "Visual Framing",
                f"{visual['avg_framing']}/100"
            ],
            [
                "Face Visibility",
                f"{visual['face_visibility']}%"
            ]
        ]

        qtable = Table(
            question_table,
            colWidths=[285, 175],
            repeatRows=1
        )

        qtable.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#6366f1")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#d1d5db")
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f8fafc")
                    ]
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                )
            ])
        )

        story.append(qtable)
        story.append(Spacer(1, 7))

        matched = data.get(
            "matched_keywords",
            []
        )

        if matched:

            story.append(
                Paragraph(
                    "<b>Concepts Detected:</b> " +
                    escape(
                        ", ".join(matched)
                    ),
                    body_style
                )
            )

        feedback = data.get(
            "feedback",
            []
        )

        if feedback:

            story.append(
                Paragraph(
                    "<b>Question Feedback:</b>",
                    body_style
                )
            )

            for feedback_item in feedback:

                story.append(
                    Paragraph(
                        "• " +
                        escape(feedback_item),
                        small_style
                    )
                )

        story.append(Spacer(1, 15))

    # -----------------------------------------------------
    # FINAL RECOMMENDATION
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Final Summary & Practice Recommendation",
            heading_style
        )
    )

    story.append(
        Paragraph(
            escape(
                final_summary["performance"]
            ),
            body_style
        )
    )

    story.append(
        Paragraph(
            "<b>Strengths observed</b>",
            subheading_style
        )
    )

    for strength in final_summary["strengths"]:

        story.append(
            Paragraph(
                "• " +
                escape(strength),
                body_style
            )
        )

    story.append(
        Paragraph(
            "<b>Priority practice areas</b>",
            subheading_style
        )
    )

    for focus_item in final_summary["focus"]:

        story.append(
            Paragraph(
                "• " +
                escape(focus_item),
                body_style
            )
        )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Suggested practice approach:</b> "
            "Practice 2–3 mock interviews regularly. For technical "
            "questions, use a Definition → Explanation → Example "
            "structure. For HR questions, use a Situation → Action → "
            "Result structure where appropriate. Compare your recorded "
            "answer with the Best Fitting Answer for every question "
            "and focus on the concepts or communication areas that "
            "you missed.",
            body_style
        )
    )

    story.append(Spacer(1, 15))

    # -----------------------------------------------------
    # INTERPRETATION NOTE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Interpretation Note",
            heading_style
        )
    )

    story.append(
        Paragraph(
            escape(
                "Confidence and nervousness are heuristic "
                "interview-performance indicators derived from answer "
                "quality, speech behaviour and camera/visual signals. "
                "They are not psychological measurements. Facial-expression "
                "labels are AI-estimated patterns and should not be "
                "interpreted as direct measurements of actual emotions."
            ),
            small_style
        )
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            escape(
                "Speech transcription is generated automatically and may "
                "contain recognition errors. Question relevance is estimated "
                "using predefined concepts associated with each question. "
                "Best Fitting Answer is a model answer provided for comparison "
                "and should be adapted to the candidate's own experience and wording."
            ),
            small_style
        )
    )

    # -----------------------------------------------------
    # BUILD PDF
    # -----------------------------------------------------

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="title">🎤 AI Mock Interview Simulator</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Practice • Speak • Analyse • Improve'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ Interview Settings")

    role = st.selectbox(
        "Select Role",
        list(QUESTION_BANK.keys())
    )

    difficulty = st.selectbox(
        "Difficulty",
        ["Easy", "Medium", "Hard"]
    )

    interview_type = st.selectbox(
        "Interview Type",
        ["Technical", "HR"]
    )

    uploaded_resume = st.file_uploader(
        "Upload Resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_resume is not None:

        if st.session_state.resume_name != uploaded_resume.name:

            st.session_state.resume_text = (
                extract_resume_text(
                    uploaded_resume
                )
            )

            st.session_state.resume_name = (
                uploaded_resume.name
            )

        st.success(
            f"Resume loaded: {uploaded_resume.name}"
        )

    st.divider()

    if st.button(
        "🔄 Reset Interview",
        use_container_width=True
    ):

        reset_interview()

        st.rerun()


# =========================================================
# FINISHED REPORT
# =========================================================

if st.session_state.finished:

    st.header(
        "📊 Interview Performance Report"
    )

    def average(values):

        if not values:
            return 0

        return round(
            float(np.mean(values)),
            1
        )

    avg_score = average(
        st.session_state.scores
    )

    avg_relevance = average(
        st.session_state.relevance_scores
    )

    avg_communication = average(
        st.session_state.communication_scores
    )

    avg_completeness = average(
        st.session_state.completeness_scores
    )

    avg_confidence = average(
        st.session_state.confidence_indicators
    )

    avg_nervousness = average(
        st.session_state.nervousness_indicators
    )

    avg_fluency = average(
        st.session_state.fluency_scores
    )

    avg_wpm = average(
        st.session_state.words_per_minute
    )

    avg_filler = average(
        st.session_state.filler_word_counts
    )

    visual_summary = calculate_visual_summary(
        st.session_state.visual_history
    )

    improvements = get_improvement_areas(
        avg_communication,
        avg_completeness,
        avg_relevance,
        avg_fluency,
        avg_confidence,
        avg_nervousness,
        avg_wpm,
        avg_filler,
        visual_summary
    )

    final_summary = get_final_summary(
        avg_score,
        avg_relevance,
        avg_communication,
        avg_completeness,
        avg_fluency,
        avg_confidence,
        avg_nervousness,
        avg_wpm,
        avg_filler,
        visual_summary
    )

    # -----------------------------------------------------
    # OVERALL METRICS
    # -----------------------------------------------------

    cols = st.columns(4)

    with cols[0]:

        st.metric(
            "Overall",
            f"{avg_score}/10"
        )

    with cols[1]:

        st.metric(
            "Relevance",
            f"{avg_relevance}/10"
        )

    with cols[2]:

        st.metric(
            "Communication",
            f"{avg_communication}/10"
        )

    with cols[3]:

        st.metric(
            "Completeness",
            f"{avg_completeness}/10"
        )

    st.divider()

    # -----------------------------------------------------
    # SPEECH BEHAVIOUR
    # -----------------------------------------------------

    st.subheader(
        "🗣️ Speech & Interview Behaviour"
    )

    cols = st.columns(4)

    with cols[0]:

        st.metric(
            "Confidence Indicator",
            f"{avg_confidence}/100"
        )

    with cols[1]:

        st.metric(
            "Nervousness Indicator",
            f"{avg_nervousness}/100"
        )

    with cols[2]:

        st.metric(
            "Fluency",
            f"{avg_fluency}/10"
        )

    with cols[3]:

        st.metric(
            "Average WPM",
            f"{avg_wpm}"
        )

    st.info(
        "These are AI-generated interview-performance indicators "
        "based on answer quality, communication, speech behaviour "
        "and visual interview signals. They are not psychological measurements."
    )

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    st.subheader(
        "🧾 Final Summary"
    )

    st.write(
        final_summary["performance"]
    )

    summary_cols = st.columns(2)

    with summary_cols[0]:

        st.markdown(
            "**✅ Key Strengths**"
        )

        for item in final_summary["strengths"]:

            st.write(
                "• " + item
            )

    with summary_cols[1]:

        st.markdown(
            "**🎯 Primary Focus Areas**"
        )

        for item in final_summary["focus"]:

            st.write(
                "• " + item
            )

    # -----------------------------------------------------
    # VISUAL
    # -----------------------------------------------------

    st.subheader(
        "👤 Continuous Visual Interview Analysis"
    )

    visual_cols = st.columns(4)

    with visual_cols[0]:

        st.metric(
            "Average Framing",
            f"{visual_summary['avg_framing']}/100"
        )

    with visual_cols[1]:

        st.metric(
            "Face Visibility",
            f"{visual_summary['face_visibility']}%"
        )

    with visual_cols[2]:

        st.metric(
            "Visual Samples",
            visual_summary["samples"]
        )

    with visual_cols[3]:

        st.metric(
            "Dominant Expression",
            visual_summary["dominant_expression"]
        )

    st.caption(
        "Expression labels represent AI-estimated facial-expression "
        "patterns from sampled video frames. They should not be interpreted "
        "as direct measurements of actual emotions."
    )

    if visual_summary["expressions"]:

        st.bar_chart(
            visual_summary["expressions"]
        )

    # -----------------------------------------------------
    # QUESTION-WISE
    # -----------------------------------------------------

    st.subheader(
        "📝 Question-wise Performance"
    )

    for i, question in enumerate(
        st.session_state.questions
    ):

        with st.expander(
            f"Q{i + 1}. {question}"
        ):

            # ---------------------------------------------
            # YOUR ANSWER
            # ---------------------------------------------

            st.markdown(
                '<div class="answer-box">',
                unsafe_allow_html=True
            )

            st.markdown(
                "### 🎤 Your Answer"
            )

            if i < len(
                st.session_state.answers
            ):

                user_answer = (
                    st.session_state.answers[i]
                )

                if user_answer.strip():

                    st.write(
                        user_answer
                    )

                else:

                    st.warning(
                        "No answer was successfully transcribed."
                    )

            else:

                st.warning(
                    "No answer was recorded."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            # ---------------------------------------------
            # BEST FITTING ANSWER
            # ---------------------------------------------

            best_answer = get_best_fitting_answer(
                question
            )

            st.markdown(
                '<div class="best-answer-box">',
                unsafe_allow_html=True
            )

            st.markdown(
                "### ✅ Best Fitting Answer"
            )

            st.write(
                best_answer
            )

            st.caption(
                "Model answer for comparison. The candidate should use their own "
                "experience and wording rather than memorizing it word-for-word."
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            # ---------------------------------------------
            # ANSWER ANALYSIS
            # ---------------------------------------------

            if i < len(
                st.session_state.answer_metrics
            ):

                data = (
                    st.session_state.answer_metrics[i]
                )

                st.markdown(
                    "### 📊 Answer Analysis"
                )

                cols = st.columns(4)

                with cols[0]:

                    st.metric(
                        "Overall",
                        f"{data['overall']}/10"
                    )

                with cols[1]:

                    st.metric(
                        "Relevance",
                        f"{data['relevance']}/10"
                    )

                with cols[2]:

                    st.metric(
                        "Communication",
                        f"{data['communication']}/10"
                    )

                with cols[3]:

                    st.metric(
                        "Completeness",
                        f"{data['completeness']}/10"
                    )

                cols2 = st.columns(4)

                with cols2[0]:

                    st.metric(
                        "Words",
                        data["word_count"]
                    )

                with cols2[1]:

                    st.metric(
                        "Filler Words",
                        data["filler_count"]
                    )

                with cols2[2]:

                    st.metric(
                        "WPM",
                        data["wpm"]
                    )

                with cols2[3]:

                    st.metric(
                        "Fluency",
                        f"{data['fluency']}/10"
                    )

                cols3 = st.columns(2)

                with cols3[0]:

                    st.metric(
                        "Confidence Indicator",
                        f"{data['confidence']}/100"
                    )

                with cols3[1]:

                    st.metric(
                        "Nervousness Indicator",
                        f"{data['nervousness']}/100"
                    )

                matched = data.get(
                    "matched_keywords",
                    []
                )

                if matched:

                    st.success(
                        "Concepts detected: " +
                        ", ".join(matched)
                    )

                feedback = data.get(
                    "feedback",
                    []
                )

                if feedback:

                    st.write(
                        "**Feedback:**"
                    )

                    for item in feedback:

                        st.write(
                            "• " + item
                        )

            # ---------------------------------------------
            # VISUAL ANALYSIS
            # ---------------------------------------------

            q_visual = calculate_visual_summary(
                st.session_state.question_visual_history.get(
                    i,
                    []
                )
            )

            st.write(
                "### 👤 Question-wise Visual Analysis"
            )

            cols = st.columns(4)

            with cols[0]:

                st.metric(
                    "Samples",
                    q_visual["samples"]
                )

            with cols[1]:

                st.metric(
                    "Framing",
                    f"{q_visual['avg_framing']}/100"
                )

            with cols[2]:

                st.metric(
                    "Face Visibility",
                    f"{q_visual['face_visibility']}%"
                )

            with cols[3]:

                st.metric(
                    "Expression",
                    q_visual["dominant_expression"]
                )

    # -----------------------------------------------------
    # SMART IMPROVEMENT AREAS
    # -----------------------------------------------------

    st.subheader(
        "📌 Areas to Work On"
    )

    for item in improvements:

        st.write(
            "• " + item
        )

    # -----------------------------------------------------
    # FINAL VERDICT
    # -----------------------------------------------------

    if avg_score >= 8:

        st.success(
            "🎯 Overall Performance: Strong"
        )

    elif avg_score >= 6:

        st.info(
            "🎯 Overall Performance: Moderate"
        )

    else:

        st.warning(
            "🎯 Overall Performance: Needs Improvement"
        )

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "📄 Download Comprehensive Report"
    )

    if REPORTLAB_AVAILABLE:

        pdf_bytes = build_pdf_report()

        st.download_button(
            label="📥 Download Full PDF Report",
            data=pdf_bytes,
            file_name="AI_Mock_Interview_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    else:

        st.warning(
            "PDF generation requires reportlab."
        )

        st.code(
            ".\\venv313\\Scripts\\python.exe -m pip install reportlab"
        )

    if st.button(
        "🔄 Start New Interview",
        use_container_width=True
    ):

        reset_interview()

        st.rerun()

    st.stop()


# =========================================================
# INTERVIEW IN PROGRESS
# =========================================================

if st.session_state.started:

    # =====================================================
    # CAMERA
    # =====================================================

    st.header(
        "🎥 Continuous Interview Camera"
    )

    st.caption(
        "Keep your face visible. The system samples the live camera "
        "approximately every 5 seconds."
    )

    webrtc_ctx = webrtc_streamer(
        key="mock-interview-camera",
        video_processor_factory=InterviewVideoProcessor,
        media_stream_constraints={
            "video": True,
            "audio": False
        },
        async_processing=True
    )

    # =====================================================
    # CONTINUOUS VISUAL ANALYSIS
    # =====================================================

    @st.fragment(run_every="5s")
    def live_visual_analysis():

        if not webrtc_ctx.state.playing:

            st.info(
                "📷 Start the camera to begin continuous visual analysis."
            )

            return

        processor = (
            webrtc_ctx.video_processor
        )

        if processor is None:

            st.info(
                "Waiting for camera frames..."
            )

            return

        if processor.latest_frame is None:

            st.info(
                "Waiting for camera frame..."
            )

            return

        frame = processor.latest_frame.copy()

        success, encoded = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:
            return

        visual_result, annotated = (
            analyze_visual_snapshot(
                encoded.tobytes()
            )
        )

        if visual_result is None:
            return

        current_q = (
            st.session_state.current_question
        )

        visual_result["question_number"] = (
            current_q + 1
        )

        st.session_state.continuous_visual_result = (
            visual_result
        )

        st.session_state.visual_history.append(
            visual_result.copy()
        )

        if current_q not in (
            st.session_state.question_visual_history
        ):

            st.session_state.question_visual_history[
                current_q
            ] = []

        st.session_state.question_visual_history[
            current_q
        ].append(
            visual_result.copy()
        )

        st.session_state.current_annotated_frame = (
            annotated
        )

        cols = st.columns(4)

        with cols[0]:

            st.metric(
                "Face",
                "Detected"
                if visual_result["face_detected"]
                else "Not detected"
            )

        with cols[1]:

            st.metric(
                "Framing",
                f"{visual_result['framing_score']}/100"
            )

        with cols[2]:

            st.metric(
                "Expression",
                visual_result["expression"]
            )

        with cols[3]:

            st.metric(
                "Position",
                visual_result["face_position"]
            )

        if annotated is not None:

            st.image(
                cv2.cvtColor(
                    annotated,
                    cv2.COLOR_BGR2RGB
                ),
                caption=(
                    f"Continuous visual sample • "
                    f"Question {current_q + 1}"
                ),
                use_container_width=True
            )

        st.caption(
            "AI-estimated facial expression and visual indicators "
            "are not direct measurements of actual emotions."
        )

    live_visual_analysis()

    st.divider()

    # =====================================================
    # QUESTION
    # =====================================================

    current = (
        st.session_state.current_question
    )

    questions = (
        st.session_state.questions
    )

    if current >= len(questions):

        st.session_state.finished = True

        st.rerun()

    question = questions[current]

    st.progress(
        (current + 1) / len(questions)
    )

    st.markdown(
        f"""
        <div class="question-box">
            <h2>Question {current + 1} of {len(questions)}</h2>
            <h3>{question}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "🔊 Read Question Aloud"
    ):

        speak_question(
            question
        )

    # =====================================================
    # ANSWER RECORDING
    # =====================================================

    st.subheader(
        "🎤 Record Your Answer"
    )

    st.caption(
        "Speak naturally. Try to give a structured answer "
        "with a definition, explanation and example where appropriate."
    )

    audio_value = st.audio_input(
        "Record your answer"
    )

    if audio_value is not None:

        audio_bytes = (
            audio_value.getvalue()
        )

        audio_hash = hashlib.md5(
            audio_bytes
        ).hexdigest()

        if (
            st.session_state.last_processed_audio_hash.get(
                current
            ) != audio_hash
        ):

            st.session_state.last_processed_audio_hash[
                current
            ] = audio_hash

            with tempfile.TemporaryDirectory() as temp_dir:

                webm_path = os.path.join(
                    temp_dir,
                    "answer.webm"
                )

                wav_path = os.path.join(
                    temp_dir,
                    "answer.wav"
                )

                with open(
                    webm_path,
                    "wb"
                ) as f:

                    f.write(
                        audio_bytes
                    )

                try:

                    subprocess.run(
                        [
                            FFMPEG_PATH,
                            "-y",
                            "-i",
                            webm_path,
                            "-ar",
                            "16000",
                            "-ac",
                            "1",
                            wav_path
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )

                    with wave.open(
                        wav_path,
                        "rb"
                    ) as wf:

                        duration_seconds = (
                            wf.getnframes() /
                            wf.getframerate()
                        )

                    recognizer = sr.Recognizer()

                    with sr.AudioFile(
                        wav_path
                    ) as source:

                        audio_data = (
                            recognizer.record(
                                source
                            )
                        )

                    try:

                        result = recognizer.recognize_google(
                            audio_data,
                            language="en-IN",
                            show_all=True
                        )

                        if isinstance(
                            result,
                            dict
                        ):

                            alternatives = (
                                result.get(
                                    "alternative",
                                    []
                                )
                            )

                            if alternatives:

                                answer = alternatives[0].get(
                                    "transcript",
                                    ""
                                )

                            else:

                                answer = ""

                        else:

                            answer = str(result)

                    except sr.UnknownValueError:

                        answer = ""

                    except sr.RequestError as e:

                        st.error(
                            f"Speech recognition service error: {e}"
                        )

                        answer = ""

                    if answer.strip():

                        answer_data = analyze_answer(
                            question,
                            answer
                        )

                        word_count = (
                            answer_data["word_count"]
                        )

                        filler_count = (
                            count_filler_words(
                                answer
                            )
                        )

                        filler_density = (
                            filler_count /
                            max(1, word_count)
                        ) * 100

                        wpm = (
                            word_count /
                            (duration_seconds / 60)
                            if duration_seconds > 0
                            else 0
                        )

                        wpm = round(
                            wpm,
                            1
                        )

                        fluency = (
                            calculate_fluency(
                                word_count,
                                duration_seconds
                            )
                        )

                        visual = (
                            st.session_state.continuous_visual_result
                        )

                        if visual is None:

                            framing = 0
                            face_detected = False

                        else:

                            framing = visual.get(
                                "framing_score",
                                0
                            )

                            face_detected = visual.get(
                                "face_detected",
                                False
                            )

                        confidence = (
                            calculate_confidence(
                                answer_data,
                                fluency,
                                framing
                            )
                        )

                        nervousness = (
                            calculate_nervousness(
                                filler_density,
                                fluency,
                                word_count,
                                answer_data["communication"],
                                framing,
                                face_detected
                            )
                        )

                        feedback = get_feedback(
                            question,
                            answer_data,
                            filler_count,
                            wpm,
                            fluency,
                            confidence,
                            nervousness
                        )

                        answer_data.update({

                            "answer": answer,

                            "best_fitting_answer":
                                get_best_fitting_answer(
                                    question
                                ),

                            "duration": round(
                                duration_seconds,
                                1
                            ),

                            "filler_count":
                                filler_count,

                            "wpm":
                                wpm,

                            "fluency":
                                fluency,

                            "confidence":
                                confidence,

                            "nervousness":
                                nervousness,

                            "feedback":
                                feedback
                        })

                        # ---------------------------------
                        # SAVE / REPLACE ANSWER
                        # ---------------------------------

                        while len(
                            st.session_state.answers
                        ) <= current:

                            st.session_state.answers.append(
                                ""
                            )

                        while len(
                            st.session_state.answer_metrics
                        ) <= current:

                            st.session_state.answer_metrics.append(
                                {}
                            )

                        while len(
                            st.session_state.scores
                        ) <= current:

                            st.session_state.scores.append(
                                0
                            )

                        while len(
                            st.session_state.relevance_scores
                        ) <= current:

                            st.session_state.relevance_scores.append(
                                0
                            )

                        while len(
                            st.session_state.communication_scores
                        ) <= current:

                            st.session_state.communication_scores.append(
                                0
                            )

                        while len(
                            st.session_state.completeness_scores
                        ) <= current:

                            st.session_state.completeness_scores.append(
                                0
                            )

                        while len(
                            st.session_state.keyword_counts
                        ) <= current:

                            st.session_state.keyword_counts.append(
                                0
                            )

                        st.session_state.answers[
                            current
                        ] = answer

                        st.session_state.answer_metrics[
                            current
                        ] = answer_data

                        st.session_state.scores[
                            current
                        ] = answer_data["overall"]

                        st.session_state.relevance_scores[
                            current
                        ] = answer_data["relevance"]

                        st.session_state.communication_scores[
                            current
                        ] = answer_data["communication"]

                        st.session_state.completeness_scores[
                            current
                        ] = answer_data["completeness"]

                        st.session_state.keyword_counts[
                            current
                        ] = answer_data["keyword_count"]

                        while len(
                            st.session_state.filler_word_counts
                        ) <= current:

                            st.session_state.filler_word_counts.append(
                                0
                            )

                        while len(
                            st.session_state.speech_word_counts
                        ) <= current:

                            st.session_state.speech_word_counts.append(
                                0
                            )

                        while len(
                            st.session_state.answer_durations
                        ) <= current:

                            st.session_state.answer_durations.append(
                                0
                            )

                        while len(
                            st.session_state.words_per_minute
                        ) <= current:

                            st.session_state.words_per_minute.append(
                                0
                            )

                        while len(
                            st.session_state.fluency_scores
                        ) <= current:

                            st.session_state.fluency_scores.append(
                                0
                            )

                        while len(
                            st.session_state.confidence_indicators
                        ) <= current:

                            st.session_state.confidence_indicators.append(
                                0
                            )

                        while len(
                            st.session_state.nervousness_indicators
                        ) <= current:

                            st.session_state.nervousness_indicators.append(
                                0
                            )

                        st.session_state.filler_word_counts[
                            current
                        ] = filler_count

                        st.session_state.speech_word_counts[
                            current
                        ] = word_count

                        st.session_state.answer_durations[
                            current
                        ] = round(
                            duration_seconds,
                            1
                        )

                        st.session_state.words_per_minute[
                            current
                        ] = wpm

                        st.session_state.fluency_scores[
                            current
                        ] = fluency

                        st.session_state.confidence_indicators[
                            current
                        ] = confidence

                        st.session_state.nervousness_indicators[
                            current
                        ] = nervousness

                        # =================================
                        # DISPLAY RESULT
                        # =================================

                        st.success(
                            "Answer successfully analysed."
                        )

                        # ---------------------------------
                        # YOUR ANSWER
                        # ---------------------------------

                        st.markdown(
                            '<div class="answer-box">',
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            "### 🎤 Your Answer"
                        )

                        st.write(
                            answer
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ---------------------------------
                        # BEST FITTING ANSWER
                        # ---------------------------------

                        st.markdown(
                            '<div class="best-answer-box">',
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            "### ✅ Best Fitting Answer"
                        )

                        st.write(
                            get_best_fitting_answer(
                                question
                            )
                        )

                        st.caption(
                            "This is a model answer for comparison. "
                            "Your own answer should be expressed naturally in your own words."
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        # ---------------------------------
                        # SCORE
                        # ---------------------------------

                        st.markdown(
                            "### 📊 Your Answer Analysis"
                        )

                        cols = st.columns(4)

                        with cols[0]:

                            st.metric(
                                "Score",
                                f"{answer_data['overall']}/10"
                            )

                        with cols[1]:

                            st.metric(
                                "WPM",
                                wpm
                            )

                        with cols[2]:

                            st.metric(
                                "Filler Words",
                                filler_count
                            )

                        with cols[3]:

                            st.metric(
                                "Fluency",
                                f"{fluency}/10"
                            )

                        cols = st.columns(2)

                        with cols[0]:

                            st.metric(
                                "Confidence Indicator",
                                f"{confidence}/100"
                            )

                        with cols[1]:

                            st.metric(
                                "Nervousness Indicator",
                                f"{nervousness}/100"
                            )

                        if answer_data[
                            "matched_keywords"
                        ]:

                            st.info(
                                "Concepts detected: " +
                                ", ".join(
                                    answer_data[
                                        "matched_keywords"
                                    ]
                                )
                            )

                        st.write(
                            "**Feedback:**"
                        )

                        for item in feedback:

                            st.write(
                                "• " + item
                            )

                    else:

                        st.warning(
                            "I could not understand the recording. "
                            "Please record your answer again."
                        )

                except Exception as e:

                    st.error(
                        f"Audio processing error: {e}"
                    )

    # =====================================================
    # NAVIGATION
    # =====================================================

    st.divider()

    nav1, nav2 = st.columns(2)

    with nav1:

        if st.button(
            "➡️ Next Question",
            use_container_width=True
        ):

            st.session_state.question_history.append({
                "question": question,
                "answer": (
                    st.session_state.answers[current]
                    if current < len(
                        st.session_state.answers
                    )
                    else ""
                ),
                "best_fitting_answer":
                    get_best_fitting_answer(
                        question
                    )
            })

            st.session_state.current_question += 1

            st.session_state.continuous_visual_result = None
            st.session_state.current_annotated_frame = None

            if (
                st.session_state.current_question
                >= len(
                    st.session_state.questions
                )
            ):

                st.session_state.finished = True

            st.rerun()

    with nav2:

        if st.button(
            "🏁 Finish Interview",
            use_container_width=True
        ):

            st.session_state.finished = True

            st.rerun()

    st.stop()


# =========================================================
# START SCREEN
# =========================================================

st.subheader(
    "🚀 Start Your AI Mock Interview"
)

st.write(
    "Configure your interview from the sidebar and start when ready."
)


# =========================================================
# RESUME STATUS
# =========================================================

if st.session_state.resume_text:

    st.success(
        f"Resume ready: {st.session_state.resume_name}"
    )

else:

    st.info(
        "Resume upload is optional."
    )


# =========================================================
# QUESTION PREVIEW
# =========================================================

preview_questions = QUESTION_BANK[
    role
][
    interview_type
][
    difficulty
]

st.subheader(
    "📋 Question Preview"
)

for i, q in enumerate(
    preview_questions[:3]
):

    st.write(
        f"**{i + 1}.** {q}"
    )

st.caption(
    f"{len(preview_questions)} questions are available "
    f"for {role} → {interview_type} → {difficulty}."
)


# =========================================================
# NUMBER OF QUESTIONS
# =========================================================

question_count = st.slider(
    "Number of questions",
    min_value=3,
    max_value=min(
        10,
        len(preview_questions)
    ),
    value=min(
        5,
        len(preview_questions)
    )
)


# =========================================================
# START INTERVIEW
# =========================================================

if st.button(
    "🎬 Start Interview",
    type="primary",
    use_container_width=True
):

    reset_interview()

    selected_questions = random.sample(
        preview_questions,
        question_count
    )

    st.session_state.questions = (
        selected_questions
    )

    st.session_state.role = role

    st.session_state.difficulty = (
        difficulty
    )

    st.session_state.interview_type = (
        interview_type
    )

    st.session_state.started = True

    st.session_state.finished = False

    st.session_state.interview_start_time = (
        time.time()
    )

    st.rerun()