"""
Evaluation dataset generator.
Creates a sample Q&A dataset for evaluating the RAG pipeline's quality.
"""

import json
import os


# Sample evaluation dataset — expand with real document-based Q&A pairs
EVAL_DATASET = [
    {
        "question": "What is the company's vacation policy?",
        "ground_truth": "Employees are entitled to annual paid vacation based on their tenure.",
        "expected_source": "HR_Policy.pdf",
        "category": "hr",
    },
    {
        "question": "What is the procedure for system restart?",
        "ground_truth": "The system restart procedure involves notifying the team, saving state, and executing the restart command.",
        "expected_source": "Technical_Manual.pdf",
        "category": "engineering",
    },
    {
        "question": "What are the expense reimbursement limits?",
        "ground_truth": "Expense reimbursement limits vary by category: meals up to $50/day, travel expenses require pre-approval.",
        "expected_source": "Finance_Policy.pdf",
        "category": "finance",
    },
    {
        "question": "How do I request remote work?",
        "ground_truth": "Remote work requests must be submitted through the HR portal with manager approval.",
        "expected_source": "HR_Policy.pdf",
        "category": "hr",
    },
    {
        "question": "What is the data backup schedule?",
        "ground_truth": "Full backups are performed weekly, incremental backups run nightly at 2 AM.",
        "expected_source": "Technical_Manual.pdf",
        "category": "engineering",
    },
    {
        "question": "What is the password policy?",
        "ground_truth": "Passwords must be at least 12 characters with uppercase, lowercase, numbers, and special characters. Changed every 90 days.",
        "expected_source": "Security_Policy.pdf",
        "category": "public",
    },
    {
        "question": "What are the office hours?",
        "ground_truth": "Standard office hours are 9:00 AM to 6:00 PM, Monday through Friday.",
        "expected_source": "Employee_Handbook.pdf",
        "category": "public",
    },
    {
        "question": "How is the annual performance review conducted?",
        "ground_truth": "Annual performance reviews are conducted in Q4 with self-assessment, manager review, and 360 feedback.",
        "expected_source": "HR_Policy.pdf",
        "category": "hr",
    },
]


def generate_eval_dataset(output_path: str = None) -> list[dict]:
    """
    Generate evaluation dataset and save to a JSON file.
    Returns the dataset as a list of dicts.
    """
    if output_path is None:
        output_path = os.path.join("evaluation", "results", "eval_dataset.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(EVAL_DATASET, f, indent=2, ensure_ascii=False)

    print(f"Evaluation dataset saved to {output_path} ({len(EVAL_DATASET)} samples)")
    return EVAL_DATASET


def load_eval_dataset(path: str = None) -> list[dict]:
    """Load evaluation dataset from JSON file."""
    if path is None:
        path = os.path.join("evaluation", "results", "eval_dataset.json")

    if not os.path.exists(path):
        print("Dataset not found. Generating default dataset...")
        return generate_eval_dataset(path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    dataset = generate_eval_dataset()
    print(f"Generated {len(dataset)} evaluation samples")
    for item in dataset:
        print(f"  - [{item['category']}] {item['question']}")
