# Dishstars

## Overview
Dishstars is an innovative application that revolutionizes the way food lovers discover new dining experiences. Unlike traditional platforms that focus on recommending restaurants based on overall ratings, Dishstars provides recommendations based on specific dishes. This dish-centric approach helps users find the best culinary experiences tailored to their tastes. The project was conceived and executed as a rapid three-week endeavor, and although the codebase is outdated and not expected to run, it serves as a showcase of the application's capabilities and the technologies employed.

**[Watch Dishstars in action on YouTube!](https://www.youtube.com/watch?v=lSJvYbkjcS4)**

## Problem Statement
When searching for dining options, most platforms offer recommendations based on restaurant ratings, which don't necessarily reflect the quality of individual dishes. Dishstars addresses this gap by analyzing user reviews to highlight standout dishes, enabling users to make more informed decisions based on what's actually served.

## Repository Contents
This repository includes all the code and resources used to build Dishstars. Here's what you'll find in each directory:

### Flex Services Module (`flexservices/`)
- **`app.yaml`**: Configures the Google App Engine environment for backend services.
- **`appengine_config.py`**: Contains configuration settings for the App Engine application.
- **`dishrecommender.py`**: Implements the logic to analyze user reviews and identify popular dishes.
- **`dishstars_firebase.py`**: Manages interactions with Firebase for data storage and retrieval.
- **`geodish.py`**: Provides geolocation-based dish recommendations.
- **`google_language.py`**: Uses Google NLP API for sentiment analysis and entity recognition.
- **`gunicorn.conf.py`**: Configuration for Gunicorn, optimizing web service performance.
- **`main.py`**: Main entry point for backend services, setting up web application routing.
- **`requirements.txt`**: Lists Python dependencies for the flex services.

### Main Application Module (`mainapp/`)
- **`app.yaml`**: Configures the Google App Engine environment for the main application.
- **`appengine_config.py`**: Sets up necessary libraries and configurations for the app.
- **`queue.yaml`**: Configures task queues for asynchronous task processing.
- **`main.py`**: Initializes and runs the web application, including routing and views.
- **`requirements.txt`**: Lists dependencies for the main application module.
- **Static Files and Templates**:
  - **Images** (`static/images/`): Contains static assets like the Dishstars logo.
  - **HTML Templates** (`templates/`): Includes `savedlist.html` and `searchresults.html` for user interfaces.

### Regional Data (`mainapp/regions/`)
- **Text files** (`regions_la.txt`, `regions_orange.txt`, etc.): Contain data for localizing dish recommendations across different regions.

## Technologies Used
- **Google Cloud Platform (GCP)**
- **Google NLP API**: For sentiment analysis and entity recognition.
- **Firebase**: Used for data storage and real-time updates.
- **Python & NLTK**: Main programming language and toolkit for natural language processing tasks.

## Setup and Installation
Note: The code in this repository is outdated and is not intended to be run as a functional application. It is provided for historical context and as a portfolio piece.

## Contributing
While this project is no longer active, I welcome feedback and discussions on similar projects or collaborations. Feel free to reach out or fork this repository to experiment with the ideas presented.

## License
This project is open-sourced under the MIT license.

## Contact Information
For inquiries or further information, please contact me at [Your Contact Email].

Thank you for your interest in Dishstars!
