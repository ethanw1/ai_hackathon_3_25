import arxiv
import datetime
import os
import aiohttp
import asyncio
import numpy as np
from typing import List, Dict, Any
import json
import math
import openai
from cerebras.cloud.sdk import Cerebras
import traceback

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY")


async def investigate(data):
    """
    Search arXiv for papers on a specific topic within a given time frame.

    Expected data format:
    {
        "topic": "machine learning",
        "time_frame": "week" | "month" | "year",
        "question": "What are the latest advancements in uncertainty estimation in neural networks?"
    }

    Returns a list of papers with their details.
    """
    try:
        if not OPENAI_API_KEY:
            return {
                "status": "error",
                "message": "OPENAI_API_KEY not found in environment variables",
            }

        if not CEREBRAS_API_KEY:
            return {
                "status": "error",
                "message": "CEREBRAS_API_KEY not found in environment variables",
            }
        # Extract parameters
        topic = data.get("topic", "")
        time_frame = data.get("time_frame", "week")

        # Calculate the date based on time frame - make it timezone aware
        today = datetime.datetime.now(datetime.timezone.utc)
        if time_frame == "week":
            cutoff_date = today - datetime.timedelta(days=7)
        elif time_frame == "month":
            cutoff_date = today - datetime.timedelta(days=30)
        elif time_frame == "year":
            cutoff_date = today - datetime.timedelta(days=365)
        else:
            # Default to one week if invalid time frame
            cutoff_date = today - datetime.timedelta(days=7)
            time_frame = "week"

        # Create a client instead of using deprecated Search.results()
        client = arxiv.Client()

        # Set up the search query
        search = arxiv.Search(
            query=topic, max_results=50, sort_by=arxiv.SortCriterion.SubmittedDate
        )

        # Process results
        papers = []
        # Use client.results() instead of search.results()
        for result in client.results(search):
            # Parse the publication date
            pub_date = result.published

            # Only include papers published after the cutoff date
            if pub_date.replace(tzinfo=datetime.timezone.utc) >= cutoff_date:
                papers.append(
                    {
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "summary": result.summary,
                        "published": pub_date.strftime("%Y-%m-%d"),
                        "pdf_url": result.pdf_url,
                        "entry_id": result.entry_id,
                        "comment": (
                            result.comment if hasattr(result, "comment") else None
                        ),
                        "doi": result.doi if hasattr(result, "doi") else None,
                    }
                )

        # If no question provided, use the topic as a fallback
        question = data.get("question", f"Recent developments in {topic}")
        top_3_papers = await summary_filter(papers, question)
        result_with_summary = get_summary(top_3_papers, question)
        # podcast_data = get_podcast(result_with_summary, question)
        # generate_podcast_audio_result = await generate_podcast_audio(podcast_data)
        # top_3_papers["podcast_data"] = generate_podcast_audio_result
        print(result_with_summary)
        return {
            "status": "success",
            "topic": topic,
            "time_frame": time_frame,
            "papers_count": len(papers),
            "selected_papers": top_3_papers.get(
                "selected_papers", ["No papers selected"]
            ),
            "summary": result_with_summary.get("summary", ""),
            "question": question,
            # "podcast_data": generate_podcast_audio_result
        }

    except Exception as e:
        import traceback

        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
        }


async def compare_papers(
    paper1: Dict, paper2: Dict, question: str, session: aiohttp.ClientSession
):
    """
    Compare two papers based on their relevance to the provided question using OpenAI.
    Returns 1 if paper1 is more relevant, 2 if paper2 is more relevant.
    """
    prompt = f"""
    I need to determine which of these two scientific papers is more relevant to this specific question:
    
    QUESTION: {question}
    
    PAPER 1: 
    Title: {paper1['title']}
    Summary: {paper1['summary']}
    
    PAPER 2:
    Title: {paper2['title']}
    Summary: {paper2['summary']}
    
    Based solely on relevance to the question, which paper is more relevant?
    Respond with just the number 1 or 2.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 10,
    }

    try:
        async with session.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=data
        ) as response:
            if response.status == 200:
                result = await response.json()
                answer = result["choices"][0]["message"]["content"].strip()
                # Extract just the number from the response
                if "1" in answer:
                    return 1
                elif "2" in answer:
                    return 2
                else:
                    # If unable to determine clearly, return randomly
                    return np.random.choice([1, 2])
            else:
                # In case of API error, return randomly
                print(f"API Error: {await response.text()}")
                return np.random.choice([1, 2])
    except Exception as e:
        print(f"Error comparing papers: {e}")
        return np.random.choice([1, 2])


def bradley_terry_scores(win_matrix):
    """
    Compute the Bradley-Terry model scores from a win matrix.
    This is a simple implementation using iterative approach.
    """
    n = len(win_matrix)
    # Initialize scores
    scores = np.ones(n)

    # Iteratively update scores
    for _ in range(10):  # 10 iterations usually sufficient for convergence
        for i in range(n):
            denom = 0
            for j in range(n):
                if i != j:
                    denom += (win_matrix[i, j] + win_matrix[j, i]) / (
                        scores[i] + scores[j]
                    )
            if denom > 0:
                num = np.sum(win_matrix[i, :])
                scores[i] = num / denom if num > 0 else scores[i]

    # Normalize scores to sum to 1
    return scores / np.sum(scores)


async def summary_filter(papers, question):
    """
    Filter the list of papers based on the relevance to a specific question based on the feedback of OpenAI.
    Compare each pairwise combination once of the papers asynchronously, then using the win matrix
    run a Bradley-Terry model to get the top 3 scores.
    """
    if not OPENAI_API_KEY:
        return {
            "status": "error",
            "message": "OpenAI API key not found in environment variables",
        }

    if len(papers) <= 3:
        return {"status": "success", "selected_papers": papers}

    n = len(papers)
    win_matrix = np.zeros((n, n))

    # Create all pairwise combinations
    comparisons = []
    for i in range(n):
        for j in range(i + 1, n):
            comparisons.append((i, j))

    # Execute comparisons asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, j in comparisons:
            task = compare_papers(papers[i], papers[j], question, session)
            tasks.append((i, j, asyncio.create_task(task)))

        # Await all comparison results
        for i, j, task in tasks:
            try:
                winner = await task
                if winner == 1:
                    win_matrix[i, j] += 1
                else:
                    win_matrix[j, i] += 1
            except Exception as e:
                print(f"Error in comparison task: {e}")
                # If comparison fails, randomly assign winner
                winner = np.random.choice([i, j])
                win_matrix[winner, winner ^ i ^ j] += 1

    # Calculate Bradley-Terry scores
    scores = bradley_terry_scores(win_matrix)

    # Get indices of top 3 papers by score
    top_indices = np.argsort(scores)[-3:][::-1]

    # Return top 3 papers with scores
    top_papers = []
    for idx in top_indices:
        paper = papers[idx].copy()
        paper["relevance_score"] = float(scores[idx])
        top_papers.append(paper)

    return {
        "status": "success",
        "selected_papers": top_papers,
        "total_papers_analyzed": len(papers),
    }


def get_summary(top_3_papers, question=None):
    """
    Get the summary of the top 3 papers using Cerebras API and the llama-3.3-70b model.
    """
    if not CEREBRAS_API_KEY:
        return {
            "status": "error",
            "message": "Cerebras API key not found in environment variables",
        }

    if not top_3_papers or "selected_papers" not in top_3_papers:
        return {"status": "error", "message": "No papers provided for summarization"}

    papers = top_3_papers["selected_papers"]
    if not papers:
        return {"status": "error", "message": "Empty paper list"}

    # Create formatted text for each paper
    paper_summaries = []
    for i, paper in enumerate(papers, 1):
        authors = ", ".join(paper["authors"]) if paper["authors"] else "Unknown"
        paper_summaries.append(
            f"Paper {i}:\n"
            f"Title: {paper['title']}\n"
            f"Authors: {authors}\n"
            f"Published: {paper['published']}\n"
            f"Summary: {paper['summary']}"
        )

    # Join all paper summaries with separators
    papers_text = "\n\n" + "\n\n".join(paper_summaries) + "\n\n"

    # Create prompt based on whether a question was provided
    if question:
        prompt = f"""You are an expert research assistant. I need you to analyze these scientific papers related to the question: "{question}"

{papers_text}

Please provide:
1. A concise summary of the key findings across these papers (max 200 words)
2. How relevant each paper is to my specific question, with a brief explanation of why
3. What are the most important implications of these papers for future research?
4. Any connections or contradictions between the papers
"""
    else:
        prompt = f"""You are an expert research assistant. I need you to analyze these scientific papers:

{papers_text}

Please provide:
1. A concise summary of the key findings across these papers (max 200 words)
2. A synthesis of how these papers relate to each other
3. What are the most important implications of these papers for future research?
4. Any limitations or gaps in the current research based on these papers
"""

    try:
        # Initialize Cerebras client
        client = Cerebras(
            api_key=CEREBRAS_API_KEY,
        )

        # Call the Cerebras API
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b",
        )
        # Extract the generated text
        summary_text = response.choices[0].message.content

        # Update the top_3_papers with the summary
        top_3_papers["summary"] = summary_text
        top_3_papers["question"] = question

        return top_3_papers

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating summary: {str(e)}",
            "traceback": traceback.format_exc(),
            "papers": top_3_papers[
                "selected_papers"
            ],  # Return papers even if summary fails
        }


def get_podcast(top_3_papers, question=None):
    """
    Generate a podcast script between two people discussing research papers.
    Uses Cerebras API to generate the dialogue content.

    Returns a dictionary with the podcast script and individual speaker lines.
    """
    if not CEREBRAS_API_KEY:
        return {
            "status": "error",
            "message": "Cerebras API key not found in environment variables",
        }

    if not top_3_papers or "selected_papers" not in top_3_papers:
        return {"status": "error", "message": "No papers provided for podcast creation"}

    papers = top_3_papers["selected_papers"]
    if not papers:
        return {"status": "error", "message": "Empty paper list"}

    # Create formatted text for each paper
    paper_summaries = []
    for i, paper in enumerate(papers, 1):
        authors = ", ".join(paper["authors"]) if paper["authors"] else "Unknown"
        paper_summaries.append(
            f"Paper {i}:\n"
            f"Title: {paper['title']}\n"
            f"Authors: {authors}\n"
            f"Published: {paper['published']}\n"
            f"Summary: {paper['summary']}"
        )

    # Join all paper summaries with separators
    papers_text = "\n\n" + "\n\n".join(paper_summaries) + "\n\n"

    # Get the summary if it exists
    summary = top_3_papers.get("summary", "")

    # Create prompt for podcast generation
    prompt = f"""You are a world-class podcast producer tasked with transforming the provided input text into an engaging and informative podcast script. The input may be unstructured or messy, sourced from PDFs or web pages. Your goal is to extract the most interesting and insightful content for a compelling podcast discussion.

# Input Papers:
{papers_text}

# Summary of Papers:
{summary}

# Question or Topic:
{question if question else "Recent scientific developments"}

# Steps to Follow:

1. **Analyze the Input:**
   Carefully examine the text, identifying key topics, points, and interesting facts or anecdotes that could drive an engaging podcast conversation.

2. **Craft the Dialogue:**
   Develop a natural, conversational flow between the host (Jane) and the guest speaker (Dr. Alex, an expert on the topic).

   Rules for the dialogue:
   - The host (Jane) always initiates the conversation and interviews the guest
   - Include thoughtful questions from the host to guide the discussion
   - Incorporate natural speech patterns, including occasional verbal fillers (e.g., "um," "well")
   - Allow for natural interruptions and back-and-forth between host and guest
   - Each line of dialogue should be short (no more than 100 characters)
   - Maintain a PG-rated conversation appropriate for all audiences

3. **Summarize Key Insights:**
   Naturally weave a summary of key points into the closing part of the dialogue.

Please output the podcast script as a JSON array with each element containing:
1. "speaker": either "Jane" or "Alex"
2. "text": what the speaker says (limited to 100 characters per line)

For example:
[
  {"speaker": "Jane", "text": "Welcome to the Science Express podcast! Today we're discussing quantum computing."},
  {"speaker": "Alex", "text": "Thanks, Jane. I'm excited to dive into this fascinating topic."}
]
"""

    try:
        # Initialize Cerebras client
        client = Cerebras(
            api_key=os.environ.get("CEREBRAS_API_KEY"),
        )

        # Call the Cerebras API
        response = client.generate_text(
            model="llama-3.3-70b",
            prompt=prompt,
            temperature=0.7,  # Higher temperature for creativity
            max_tokens=3000,
            top_p=0.9,
        )

        # Extract the generated text
        podcast_text = response.text if hasattr(response, "text") else str(response)

        # Try to parse as JSON, if not, return raw text
        try:
            # Find JSON array in the response
            import re

            json_match = re.search(r"\[\s*\{.*\}\s*\]", podcast_text, re.DOTALL)
            if json_match:
                podcast_json = json.loads(json_match.group(0))
            else:
                # If no valid JSON found, try to process the text into a structured format
                lines = podcast_text.split("\n")
                podcast_json = []
                current_speaker = None

                for line in lines:
                    line = line.strip()
                    if line.startswith("Jane:"):
                        current_speaker = "Jane"
                        text = line[5:].strip()
                        podcast_json.append({"speaker": current_speaker, "text": text})
                    elif line.startswith("Alex:"):
                        current_speaker = "Alex"
                        text = line[5:].strip()
                        podcast_json.append({"speaker": current_speaker, "text": text})
                    elif current_speaker and line:
                        # Continue previous speaker's line
                        podcast_json.append({"speaker": current_speaker, "text": line})

            # Separate dialogue by speaker for potential voice synthesis
            jane_lines = [
                item["text"] for item in podcast_json if item["speaker"] == "Jane"
            ]
            alex_lines = [
                item["text"] for item in podcast_json if item["speaker"] == "Alex"
            ]

            return {
                "status": "success",
                "podcast": podcast_json,
                "jane_lines": jane_lines,
                "alex_lines": alex_lines,
                "question": question,
            }

        except json.JSONDecodeError:
            # Return raw text if JSON parsing fails
            return {
                "status": "success",
                "podcast_text": podcast_text,
                "question": question,
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating podcast: {str(e)}",
            "traceback": traceback.format_exc(),
        }


async def generate_podcast_audio(podcast_data):
    """
    Generate audio for podcast dialogue using OpenAI's Text-to-Speech API.

    Parameters:
    - podcast_data: Output from get_podcast function with speaker lines

    Returns:
    - Dictionary with audio file paths
    """
    if not OPENAI_API_KEY:
        return {
            "status": "error",
            "message": "OpenAI API key not found in environment variables",
        }

    if "podcast" not in podcast_data:
        return {"status": "error", "message": "No podcast script found in data"}

    try:
        import openai
        import os
        from datetime import datetime

        # Configure OpenAI client
        openai.api_key = OPENAI_API_KEY

        # Create output directory
        output_dir = os.path.join(os.getcwd(), "podcast_audio")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique identifier for this podcast
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        podcast_id = f"podcast_{timestamp}"

        # Define voice settings
        voices = {"Jane": "nova", "Alex": "onyx"}  # Female voice  # Male voice

        # Process each line in the podcast
        audio_files = []
        full_script = []

        for i, line in enumerate(podcast_data["podcast"]):
            speaker = line["speaker"]
            text = line["text"]

            # Skip empty lines
            if not text.strip():
                continue

            # Append to full script
            full_script.append(f"{speaker}: {text}")

            # Generate speech for this line
            response = await openai.audio.speech.create(
                model="tts-1", voice=voices[speaker], input=text
            )

            # Save the audio file
            file_path = os.path.join(output_dir, f"{podcast_id}_{i:03d}_{speaker}.mp3")
            response.write_to_file(file_path)

            audio_files.append({"file": file_path, "speaker": speaker, "text": text})

        # Also save the full text script
        script_path = os.path.join(output_dir, f"{podcast_id}_script.txt")
        with open(script_path, "w") as f:
            f.write("\n".join(full_script))

        return {
            "status": "success",
            "podcast_id": podcast_id,
            "audio_files": audio_files,
            "script_file": script_path,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating audio: {str(e)}",
            "traceback": traceback.format_exc(),
        }


# Test the function
if __name__ == "__main__":
    data = {
        "topic": "machine learning",
        "time_frame": "week",
        "question": "What are the latest advancements in uncertainty estimation in neural networks?",
    }
    result = asyncio.run(investigate(data))
    print(json.dumps(result, indent=2))
# Output:
