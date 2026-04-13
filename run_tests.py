import subprocess
import sys
import os
from datetime import datetime


def run_tests(with_coverage=True, verbose=True, markers=None):
    cmd = ["pytest"]
    
    if with_coverage:
        cmd.extend([
            "--cov=.",
            "--cov-config=.coveragerc",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-report=term-missing"
        ])
    
    if verbose:
        cmd.append("-v")
    
    if markers:
        cmd.extend(["-m", markers])
    
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    return result.returncode


def run_unit_tests():
    print("\n" + "=" * 60)
    print("Running Unit Tests")
    print("=" * 60 + "\n")
    return run_tests(markers="unit")


def run_integration_tests():
    print("\n" + "=" * 60)
    print("Running Integration Tests")
    print("=" * 60 + "\n")
    return run_tests(markers="integration")


def run_all_tests():
    print("\n" + "=" * 60)
    print(f"Running All Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    return run_tests()


def generate_report():
    report_path = os.path.join(os.path.dirname(__file__), "test_report.md")
    
    result = subprocess.run(
        ["pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True
    )
    
    total_tests = result.stdout.count("<Function")
    
    coverage_result = subprocess.run(
        ["coverage", "report"],
        capture_output=True,
        text=True
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 测试报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write("## 摘要\n\n")
        f.write(f"- **测试用例总数**: {total_tests}\n")
        f.write("- **测试状态**: 请运行 `python run_tests.py` 获取最新结果\n\n")
        f.write("## 覆盖率\n\n")
        f.write("```\n")
        f.write(coverage_result.stdout)
        f.write("```\n\n")
        f.write("---\n\n")
        f.write("## 测试模块\n\n")
        f.write("| 模块 | 描述 |\n")
        f.write("|------|------|\n")
        f.write("| test_crud_users.py | CRUD 单元测试 |\n")
        f.write("| test_routers_users.py | 路由集成测试 |\n")
        f.write("| test_auth.py | 认证模块测试 |\n\n")
        f.write("## 运行命令\n\n")
        f.write("```bash\n")
        f.write("# 运行所有测试\n")
        f.write("python run_tests.py\n\n")
        f.write("# 运行带覆盖率的测试\n")
        f.write("pytest --cov=. --cov-report=html tests/\n\n")
        f.write("# 运行特定测试文件\n")
        f.write("pytest tests/test_crud_users.py -v\n")
        f.write("```\n")
    
    print(f"\nReport generated: {report_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "unit":
            exit_code = run_unit_tests()
        elif arg == "integration":
            exit_code = run_integration_tests()
        elif arg == "report":
            generate_report()
            exit_code = 0
        elif arg == "no-cov":
            exit_code = run_tests(with_coverage=False)
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: python run_tests.py [unit|integration|report|no-cov]")
            exit_code = 1
    else:
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
