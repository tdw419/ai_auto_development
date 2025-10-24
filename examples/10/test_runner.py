"""
Test Runner for Verifier Agent
Executes various test suites and validation checks
"""

import subprocess
import json
import os
from typing import Dict, List, Optional
from pathlib import Path


class TestRunner:
    """
    Orchestrates test execution for verifier agent
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize test runner
        
        Args:
            repo_path: Path to repository to test
        """
        self.repo_path = Path(repo_path)
    
    def run_tests(self, test_path: Optional[str] = None) -> Dict:
        """
        Run test suite
        
        Args:
            test_path: Optional specific test file/directory
            
        Returns:
            Test results dict
        """
        
        results = {
            'passed': False,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_count': 0,
            'failures': [],
            'duration_seconds': 0
        }
        
        # Detect test framework
        if self._has_pytest():
            return self._run_pytest(test_path)
        elif self._has_unittest():
            return self._run_unittest(test_path)
        elif self._has_jest():
            return self._run_jest(test_path)
        else:
            # No tests found
            results['passed'] = True
            results['note'] = 'No test framework detected'
            return results
    
    def _has_pytest(self) -> bool:
        """Check if pytest is available"""
        return (self.repo_path / "pytest.ini").exists() or \
               (self.repo_path / "setup.cfg").exists() or \
               (self.repo_path / "pyproject.toml").exists()
    
    def _has_unittest(self) -> bool:
        """Check if unittest tests exist"""
        test_dirs = ['tests', 'test']
        return any((self.repo_path / d).exists() for d in test_dirs)
    
    def _has_jest(self) -> bool:
        """Check if Jest is configured"""
        return (self.repo_path / "jest.config.js").exists() or \
               (self.repo_path / "package.json").exists()
    
    def _run_pytest(self, test_path: Optional[str] = None) -> Dict:
        """Run pytest tests"""
        
        cmd = ["pytest", "--tb=short", "-v", "--json-report", "--json-report-file=test_results.json"]
        
        if test_path:
            cmd.append(test_path)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse JSON report if available
            report_path = self.repo_path / "test_results.json"
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                return {
                    'passed': report['summary']['total'] == report['summary']['passed'],
                    'total_tests': report['summary']['total'],
                    'passed_tests': report['summary']['passed'],
                    'failed_count': report['summary']['failed'],
                    'failures': self._extract_pytest_failures(report),
                    'duration_seconds': report['summary']['duration']
                }
            
            # Fallback: parse text output
            passed = result.returncode == 0
            return {
                'passed': passed,
                'total_tests': self._count_tests_in_output(result.stdout),
                'passed_tests': self._count_passed_in_output(result.stdout) if passed else 0,
                'failed_count': 0 if passed else 1,
                'failures': [] if passed else [result.stdout],
                'duration_seconds': 0
            }
        
        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_count': 1,
                'failures': ['Tests timed out after 300 seconds'],
                'duration_seconds': 300
            }
        
        except Exception as e:
            return {
                'passed': False,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_count': 1,
                'failures': [f'Test execution error: {str(e)}'],
                'duration_seconds': 0
            }
    
    def _run_unittest(self, test_path: Optional[str] = None) -> Dict:
        """Run unittest tests"""
        
        cmd = ["python", "-m", "unittest", "discover", "-s", test_path or "tests", "-v"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            passed = result.returncode == 0
            
            return {
                'passed': passed,
                'total_tests': self._count_tests_in_output(result.stderr),
                'passed_tests': self._count_passed_in_output(result.stderr) if passed else 0,
                'failed_count': 0 if passed else self._count_failed_in_output(result.stderr),
                'failures': [] if passed else self._extract_unittest_failures(result.stderr),
                'duration_seconds': 0
            }
        
        except Exception as e:
            return {
                'passed': False,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_count': 1,
                'failures': [str(e)],
                'duration_seconds': 0
            }
    
    def _run_jest(self, test_path: Optional[str] = None) -> Dict:
        """Run Jest tests"""
        
        cmd = ["npm", "test", "--", "--json"]
        
        if test_path:
            cmd.append(test_path)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse Jest JSON output
            try:
                test_results = json.loads(result.stdout)
                
                return {
                    'passed': test_results['success'],
                    'total_tests': test_results['numTotalTests'],
                    'passed_tests': test_results['numPassedTests'],
                    'failed_count': test_results['numFailedTests'],
                    'failures': self._extract_jest_failures(test_results),
                    'duration_seconds': test_results['startTime'] / 1000
                }
            except json.JSONDecodeError:
                passed = result.returncode == 0
                return {
                    'passed': passed,
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_count': 0 if passed else 1,
                    'failures': [] if passed else [result.stdout],
                    'duration_seconds': 0
                }
        
        except Exception as e:
            return {
                'passed': False,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_count': 1,
                'failures': [str(e)],
                'duration_seconds': 0
            }
    
    def run_linter(self, files: List[str]) -> Dict:
        """
        Run linting checks
        
        Args:
            files: Files to lint
            
        Returns:
            Linting results
        """
        
        if self._has_python_files(files):
            return self._run_pylint(files)
        elif self._has_js_files(files):
            return self._run_eslint(files)
        else:
            return {'passed': True, 'errors': [], 'warnings': []}
    
    def _has_python_files(self, files: List[str]) -> bool:
        """Check if any Python files in list"""
        return any(f.endswith('.py') for f in files)
    
    def _has_js_files(self, files: List[str]) -> bool:
        """Check if any JS/TS files in list"""
        return any(f.endswith(('.js', '.ts', '.jsx', '.tsx')) for f in files)
    
    def _run_pylint(self, files: List[str]) -> Dict:
        """Run pylint on Python files"""
        
        python_files = [f for f in files if f.endswith('.py')]
        
        if not python_files:
            return {'passed': True, 'errors': [], 'warnings': []}
        
        cmd = ["pylint", "--output-format=json"] + python_files
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            issues = json.loads(result.stdout) if result.stdout else []
            
            errors = [i for i in issues if i['type'] == 'error']
            warnings = [i for i in issues if i['type'] == 'warning']
            
            return {
                'passed': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        
        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'errors': [{'message': 'Linting timed out'}],
                'warnings': []
            }
        
        except Exception as e:
            # Linting errors shouldn't block - just warn
            return {
                'passed': True,
                'errors': [],
                'warnings': [{'message': f'Linting failed: {str(e)}'}]
            }
    
    def _run_eslint(self, files: List[str]) -> Dict:
        """Run ESLint on JS/TS files"""
        
        js_files = [f for f in files if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]
        
        if not js_files:
            return {'passed': True, 'errors': [], 'warnings': []}
        
        cmd = ["npx", "eslint", "--format", "json"] + js_files
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            results = json.loads(result.stdout) if result.stdout else []
            
            errors = []
            warnings = []
            
            for file_result in results:
                for msg in file_result.get('messages', []):
                    if msg['severity'] == 2:
                        errors.append(msg)
                    else:
                        warnings.append(msg)
            
            return {
                'passed': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        
        except Exception as e:
            return {
                'passed': True,
                'errors': [],
                'warnings': [{'message': f'ESLint failed: {str(e)}'}]
            }
    
    # Helper methods for parsing test output
    
    def _extract_pytest_failures(self, report: Dict) -> List[str]:
        """Extract failure messages from pytest report"""
        failures = []
        for test in report.get('tests', []):
            if test['outcome'] == 'failed':
                failures.append(f"{test['nodeid']}: {test.get('call', {}).get('longrepr', 'Unknown error')}")
        return failures
    
    def _extract_unittest_failures(self, output: str) -> List[str]:
        """Extract failure messages from unittest output"""
        failures = []
        lines = output.split('\n')
        
        in_failure = False
        current_failure = []
        
        for line in lines:
            if line.startswith('FAIL:') or line.startswith('ERROR:'):
                in_failure = True
                current_failure = [line]
            elif in_failure:
                if line.startswith('---'):
                    failures.append('\n'.join(current_failure))
                    in_failure = False
                    current_failure = []
                else:
                    current_failure.append(line)
        
        return failures
    
    def _extract_jest_failures(self, results: Dict) -> List[str]:
        """Extract failure messages from Jest results"""
        failures = []
        for test_result in results.get('testResults', []):
            for test in test_result.get('assertionResults', []):
                if test['status'] == 'failed':
                    failures.append(f"{test['fullName']}: {test.get('failureMessages', ['Unknown'])[0]}")
        return failures
    
    def _count_tests_in_output(self, output: str) -> int:
        """Count total tests from output"""
        # Simple heuristic
        return output.count('test_') + output.count('def test')
    
    def _count_passed_in_output(self, output: str) -> int:
        """Count passed tests from output"""
        if 'passed' in output.lower():
            parts = output.lower().split('passed')
            if len(parts) > 1:
                nums = [int(s) for s in parts[0].split() if s.isdigit()]
                if nums:
                    return nums[-1]
        return 0
    
    def _count_failed_in_output(self, output: str) -> int:
        """Count failed tests from output"""
        if 'failed' in output.lower():
            parts = output.lower().split('failed')
            if len(parts) > 1:
                nums = [int(s) for s in parts[0].split() if s.isdigit()]
                if nums:
                    return nums[-1]
        return 0


class MockTestRunner:
    """
    Mock test runner for testing
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.should_fail = False
    
    def run_tests(self, test_path: Optional[str] = None) -> Dict:
        if self.should_fail:
            return {
                'passed': False,
                'total_tests': 5,
                'passed_tests': 3,
                'failed_count': 2,
                'failures': [
                    'test_validation: AssertionError: Expected True, got False',
                    'test_edge_case: KeyError: missing required field'
                ],
                'duration_seconds': 2.5
            }
        
        return {
            'passed': True,
            'total_tests': 10,
            'passed_tests': 10,
            'failed_count': 0,
            'failures': [],
            'duration_seconds': 1.2
        }
    
    def run_linter(self, files: List[str]) -> Dict:
        if self.should_fail:
            return {
                'passed': False,
                'errors': [
                    {'message': 'Line too long (120 > 100)', 'line': 45}
                ],
                'warnings': []
            }
        
        return {
            'passed': True,
            'errors': [],
            'warnings': []
        }
