# Meeting History

## 7th May

### Meeting Overview

This meeting was an introduction and orientation session regarding working on a project to automate the management of open-source repositories using large language models (LLMs). The meeting covered the following topics:

1. We introduced ourselves and our interests and backgrounds in AI and ML.
2. Lee and Korey, our clients from Microsoft, explained the goals and expectations of the project, as well as the benefits and opportunities for us.
3. The clients helped us set up an Azure subscription and access to AI Studio and other tools and resources.
4. The clients discussed the project brief and some possible use cases and scenarios for the solution, such as localization, documentation, validation, and social media.
5. The clients advised us to research the existing models and technologies, find an existing repo to work on and come up with a project plan and a leaflet for the next meeting.

### Key Actions 

1. To fill out the form to apply for OpenAI access with the correct subscription ID.
2. To explore the AI Studio and the models available there, as well as the GitHub extensions and actions.
3. To decide on our team structure, roles, and responsibilities.
4. To meet with our academic supervisor and validate the project brief.
5. To choose a use case and a repo to work on and define the product features and the PR statement.

## 21st May

### Meeting Overview 

1. Proposals: Made proposals to the client regarding the capabilities of the solution, including topics of localization, code analysis, and social media integration.
2. Leaflet Discussion: Our team sought to understand the client's expectations for a leaflet intended to attract end consumers. The client emphasized the importance of coherency and visuals.
3. AI Models: Discussed which models are best suited for specific tasks, mentioning various Microsoft-PHI3, Hugging Face, and OpenAI models. The client highlighted the usefulness of Azure AI Studio for deploying most of these models.

### Key Actions

1. Decide on the final solution, features, and plan of action.
2. Explore and test different models using Azure Playground to better understand the models' capabilities and effectiveness for specific tasks.
3. Begin building the leaflet with different designs using Gen AI to ensure good visuals. These designs will be presented to the client the following week.

## 28th May

### Meeting Overview
1. Final Solution: We discussed our primary objective with the client, which is to develop an app that localizes repositories based on a configuration file specifying languages.
2. Expansion: The client proposed broadening this concept to include images and code blocks, as these might present unique challenges. For instance, a code block with Chinese comments in an English README or an English image in an Arabic README.
3. Tagging Strategy: We initially considered tagging certain images and code blocks using pre-built regexes to distinguish them from regular text.
4. GPT Models: We explored the effectiveness of OpenAI GPT models in understanding prompts accurately, which might reduce the need for extensive tagging.
5. Fine Tuning: We deliberated on whether fine-tuning models with specific test and training data would be necessary for translating images and other advanced features.
6. Front End: Discussed use of front-end of our app: it should be a simple settings page. Most of the work done by developers should stay on GitHub. The only time users will interact with the app is when they want to change 1-2 settings

### Key Actions

1. Translation Bot: Develop a translation bot capable of accurately translating documents using GPT models.
2. Model Performance Testing: Evaluate the performance of various GPT models (GPT-3.5, GPT-4, GPT-4 Turbo) to identify the optimal model for accuracy and speed.
3. Edge Case Exploration: Investigate edge cases, such as handling right-to-left languages (e.g., Arabic).
4. Image Translation: Research and develop methods for translating images into the desired languages.
   
## 4th June

### Meeting Overview

1. Localization and Translation: We discussed the use of Azure's Computer Vision API for image text extraction and the potential use of generative AI for text translation in images. We considered the efficiency and cost-effectiveness of using AI services versus generic AI for specific tasks.
2. GitHub Integration: We shared progress on integrating GitHub for automatic documentation translation, including the creation of a separate branch for translations and the use of webhooks for updates. Concerns were raised about maintaining synchronization between the main and translation branches.
3. Leaflet Design: Concerns were raised about the design and content of a leaflet, including its effectiveness in conveying the product's benefits. We suggested focusing on the benefits of the solution and using generative AI for content improvement.
4. AI Model Evaluation: We discussed the limitations of using Azure AI Studio's model evaluation for our translation tool, indicating it might not be suitable for our project's needs. We considered focusing on monitoring instead of evaluation.
5. Project Collaboration: We encountered difficulties adding members to our AI Studio project, which could impact collaboration. We were tasked with reporting the issue using the feedback feature.

### Key Actions

1. Localization of Images - to explore using generative AI for replacing text in images with translated text or adding captions with translated text.
2. AI Services vs. LLM - Ayyoub to compare the effectiveness of Azure Computer Vision API against GPT-4 for extracting and translating text from images.
3. GitHub Repo Initialization - Chung to investigate the process of syncing the main branch with the Co-op translator branch automatically through GitHub actions.
4. Leaflet Design - Liu to modify the leaflet to highlight the benefits of the product more effectively and consider adding a logo generated by generative AI.
5. Translation Prompt Engineering - Belur to work on integrating the prompt engineering for game translation with the backend.
6. Monitoring Translation Costs - We are to monitor the costs associated with using GPT models for translation to ensure they stay within budget.

These action items are derived from the discussions and suggestions made during the meeting.

## 11th June

### Meeting Overview:
The meeting focused on discussing and demonstrating various aspects of our project involving document and image translation, code analysis, and repository management. Here's a summary of the key topics and actions:

1. We demonstrated translating documents and comments from English to Arabic using GPT-4, highlighting accuracy and context preservation. We confirmed the translation's accuracy and its superiority over our Arabic skills. We discussed technical details, such as the translation process and handling code blocks in documents.
2. We presented on image translation, showing improvements in text extraction from images and the translation process. We compared the model's output with Google Translate, noting better context understanding in translations. We discussed the technical aspects and potential improvements.
3. We shared our work on backend development, demonstrating how to trigger translations for repository documents and manage translations through a new branch. We discussed the need for handling pull requests and updates more effectively.
4. We mentioned exploring models for static code analysis, initially focusing on CodeBERT and considering GitHub Copilot for integration into our GitHub repository. We were provided guidance on model selection and usage.

### Key Actions:
1. Refine the document and image translation processes, especially handling file paths and linking translated documents and images correctly.
2. Improve the backend system for managing translations in repositories, ensuring updates are handled correctly post-pull request resolutions.
3. Continue exploring suitable models for static code analysis and integrate them into the GitHub repository.

## 18th June

### Meeting Overview
We participated in the meeting to discuss progress on various projects, including font issues in a notebook, static code analysis, and backend updates.

1. Font Issues in Notebook: We discussed the problem of fonts not displaying correctly for certain languages in the notebook. We decided to use Google's Noto Sans fonts, which support multiple languages, and discussed licensing issues. We also considered other font options and the need for a smart font-choosing mechanism based on language.
2. Static Code Analysis: We updated the team on the static code analysis part, mentioning the switch to the GPT model and the need to handle long code files by segmenting them. We also discussed the poster content and the need for testing the new code.
3. Backend Updates: We implemented a robust system for handling GitHub operations using a robot account, simplifying the code by removing the need to store user access tokens. We also integrated image processing into the backend translation process but faced issues with downloading large image files.
4. Image Translation: We worked on speeding up image translation by splitting images into sections for concurrent processing. However, this approach led to loss of context and inaccurate translations, so we decided to stick with the original method despite it being slower.
5. Future Plans: We discussed future plans, including benchmarking models and improving the image translation process. We also considered using Kubernetes for scaling the product and implementing a gamified section for developers.

### Key Actions

1. Font Issues in Notebook: Experiment with different fonts for various languages to ensure accurate display in the notebook.
2. Static Code Analysis: Test the new static code analysis code to ensure it functions correctly.
3. Backend Updates: Investigate the issue with downloading large image files and find a solution. Try using GitHub3 or GitPython libraries to resolve the file size issue.
4. Future Plans: Benchmark models and compare their performance for the next meeting.

## 25th June

### Meeting Overview

1. Product Presentation: We presented our product to our mentors/clients, who expressed high satisfaction with our progress.
2. Future Planning: We discussed scheduling future meetings for further presentations and plans to feature our work in a Microsoft blog.
3. Hallucination Issue in Co-operator: We addressed the problem where GPT models were adding filler material to empty files and one-liner, mitigating this issue before the meeting.
4. Evaluation Model: We showcased our evaluation model, which utilizes Hugging Face models.
5. Client Recommendation: The client suggested exploring Red Teaming (PyRIT) to identify risks and enhance the security of our solution.

### Key Actions 

1. Microsoft Blog: Follow the provided formula from the clients and complete the blog within one week.
2. Red Teaming: Use the repository provided by clients to assess and mitigate risks associated with AI usage in our solution.
3. Deployment: Deploy our solution for booth presentation purposes and general application.
4. Edge Cases: Test our solution with rare cases and unusual scenarios to identify and address edge cases, improving the overall product for end users.

