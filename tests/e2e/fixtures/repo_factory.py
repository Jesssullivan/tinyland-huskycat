"""Test repository factory for creating isolated GitOps test repositories."""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional


class TestRepoFactory:
    """Factory for creating isolated test repositories with GitOps features."""

    @staticmethod
    def create_gitops_repo(
        features: List[str],
        temp_dir: Optional[Path] = None,
    ) -> Path:
        """
        Create a test GitOps repository with specified features.

        Args:
            features: List of features to enable
                     ['gitlab_ci', 'helm', 'k8s', 'terraform', 'ansible']
            temp_dir: Optional directory (uses tempfile if None)

        Returns:
            Path to test repository
        """
        if temp_dir is None:
            temp_dir = Path(tempfile.mkdtemp(prefix="huskycat-test-"))

        repo_path = temp_dir

        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create feature files based on requested features
        if "gitlab_ci" in features:
            TestRepoFactory._create_gitlab_ci(repo_path)

        if "helm" in features:
            TestRepoFactory._create_helm_chart(repo_path)

        if "k8s" in features:
            TestRepoFactory._create_k8s_manifests(repo_path)

        if "terraform" in features:
            TestRepoFactory._create_terraform(repo_path)

        if "ansible" in features:
            TestRepoFactory._create_ansible(repo_path)

        # Create a simple Python file (most repos have code)
        TestRepoFactory._create_python_code(repo_path)

        # Initial commit
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "chore: initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    @staticmethod
    def _create_gitlab_ci(repo_path: Path) -> None:
        """Create .gitlab-ci.yml with Auto-DevOps templates."""
        ci_content = """include:
  - template: Auto-DevOps.gitlab-ci.yml
  - template: Security/SAST.gitlab-ci.yml

variables:
  AUTO_DEVOPS_PLATFORM_TARGET: ECS
  POSTGRES_ENABLED: "false"

stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - echo "Building application"
  artifacts:
    paths:
      - dist/

test:
  stage: test
  script:
    - echo "Running tests"
"""
        (repo_path / ".gitlab-ci.yml").write_text(ci_content)

    @staticmethod
    def _create_helm_chart(repo_path: Path) -> None:
        """Create Helm chart structure."""
        chart_dir = repo_path / "chart"
        chart_dir.mkdir(exist_ok=True)

        # Chart.yaml
        chart_yaml = """apiVersion: v2
name: test-app
description: Test application Helm chart
type: application
version: 0.1.0
appVersion: "1.0"
"""
        (chart_dir / "Chart.yaml").write_text(chart_yaml)

        # values.yaml
        values_yaml = """replicaCount: 2

image:
  repository: nginx
  tag: "1.21"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi
"""
        (chart_dir / "values.yaml").write_text(values_yaml)

        # templates directory
        templates_dir = chart_dir / "templates"
        templates_dir.mkdir(exist_ok=True)

        # Simple deployment template
        deployment_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Chart.Name }}
  labels:
    app: {{ .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Chart.Name }}
  template:
    metadata:
      labels:
        app: {{ .Chart.Name }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: 80
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
"""
        (templates_dir / "deployment.yaml").write_text(deployment_template)

    @staticmethod
    def _create_k8s_manifests(repo_path: Path) -> None:
        """Create Kubernetes manifest files."""
        k8s_dir = repo_path / "k8s" / "deployments"
        k8s_dir.mkdir(parents=True, exist_ok=True)

        # Deployment manifest
        deployment = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  labels:
    app: test-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 100m
            memory: 128Mi
"""
        (k8s_dir / "app.yaml").write_text(deployment)

        # Service manifest
        service_dir = repo_path / "k8s" / "services"
        service_dir.mkdir(parents=True, exist_ok=True)

        service = """apiVersion: v1
kind: Service
metadata:
  name: test-app
  labels:
    app: test-app
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  selector:
    app: test-app
"""
        (service_dir / "app.yaml").write_text(service)

    @staticmethod
    def _create_terraform(repo_path: Path) -> None:
        """Create Terraform configuration."""
        main_tf = """terraform {
  required_version = ">= 1.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

resource "kubernetes_namespace" "test" {
  metadata {
    name = "test-namespace"
  }
}

resource "kubernetes_deployment" "test_app" {
  metadata {
    name      = "test-app"
    namespace = kubernetes_namespace.test.metadata[0].name
  }

  spec {
    replicas = 2

    selector {
      match_labels = {
        app = "test-app"
      }
    }

    template {
      metadata {
        labels = {
          app = "test-app"
        }
      }

      spec {
        container {
          name  = "nginx"
          image = "nginx:1.21"

          port {
            container_port = 80
          }
        }
      }
    }
  }
}
"""
        (repo_path / "main.tf").write_text(main_tf)

        # variables.tf
        variables_tf = """variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
  default     = "test-namespace"
}

variable "replicas" {
  description = "Number of replicas"
  type        = number
  default     = 2
}
"""
        (repo_path / "variables.tf").write_text(variables_tf)

    @staticmethod
    def _create_ansible(repo_path: Path) -> None:
        """Create Ansible playbook."""
        playbooks_dir = repo_path / "playbooks"
        playbooks_dir.mkdir(exist_ok=True)

        deploy_playbook = """---
- name: Deploy application
  hosts: all
  become: yes
  tasks:
    - name: Install Docker
      apt:
        name: docker.io
        state: present
        update_cache: yes

    - name: Start Docker service
      service:
        name: docker
        state: started
        enabled: yes

    - name: Pull application image
      docker_image:
        name: nginx:1.21
        source: pull

    - name: Run application container
      docker_container:
        name: test-app
        image: nginx:1.21
        state: started
        ports:
          - "80:80"
"""
        (playbooks_dir / "deploy.yml").write_text(deploy_playbook)

        # Inventory file
        inventory = """[web]
server1 ansible_host=192.168.1.10
server2 ansible_host=192.168.1.11

[web:vars]
ansible_user=deploy
ansible_python_interpreter=/usr/bin/python3
"""
        (playbooks_dir / "inventory.ini").write_text(inventory)

    @staticmethod
    def _create_python_code(repo_path: Path) -> None:
        """Create simple Python code for testing pre-commit hooks."""
        src_dir = repo_path / "src"
        src_dir.mkdir(exist_ok=True)

        # Simple Python module
        main_py = '''"""Main application module."""


def greet(name: str) -> str:
    """
    Greet a user by name.

    Args:
        name: Name of the user to greet

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"


def main() -> None:
    """Main entry point."""
    message = greet("World")
    print(message)


if __name__ == "__main__":
    main()
'''
        (src_dir / "main.py").write_text(main_py)

        # __init__.py
        (src_dir / "__init__.py").write_text('"""Test application."""\n')

    @staticmethod
    def cleanup_repo(repo_path: Path) -> None:
        """Clean up test repository."""
        import shutil

        if repo_path.exists():
            shutil.rmtree(repo_path)

    @staticmethod
    def create_invalid_yaml_file(repo_path: Path, file_path: str) -> None:
        """Create an invalid YAML file for testing error detection."""
        invalid_yaml = """
invalid: yaml: syntax::
  - not
  proper structure
    bad indentation
"""
        (repo_path / file_path).write_text(invalid_yaml)

    @staticmethod
    def create_invalid_python_file(repo_path: Path, file_path: str) -> None:
        """Create an invalid Python file for testing pre-commit hooks."""
        invalid_python = """
def broken_function(
    # Missing closing parenthesis
    print("This won't work")
"""
        (repo_path / file_path).write_text(invalid_python)

    @staticmethod
    def get_repo_info(repo_path: Path) -> Dict[str, bool]:
        """
        Get information about what features are present in the repo.

        Args:
            repo_path: Path to repository

        Returns:
            Dictionary of detected features
        """
        return {
            "gitlab_ci": (repo_path / ".gitlab-ci.yml").exists(),
            "helm": (repo_path / "chart").exists(),
            "k8s": (repo_path / "k8s").exists(),
            "terraform": len(list(repo_path.glob("*.tf"))) > 0,
            "ansible": (repo_path / "playbooks").exists(),
            "python": (repo_path / "src").exists(),
        }
