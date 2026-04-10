#!/usr/bin/env python3
"""
代码结构测试
验证多模态功能代码结构是否正确
"""

import ast
import os

def check_imports(file_path):
    """检查文件导入"""
    print(f"检查 {file_path} 的导入...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        print(f"   找到 {len(imports)} 个导入:")
        for imp in sorted(set(imports)):
            print(f"   - {imp}")
        
        # 检查关键导入
        key_imports = [
            'PIL.Image',
            'base64',
            'io',
            'cv2',
            'numpy',
            'transformers.AutoProcessor',
            'transformers.AutoModelForVision2Seq'
        ]
        
        print("\n检查关键多模态导入:")
        missing = []
        for key_imp in key_imports:
            if any(key_imp in imp for imp in imports):
                print(f"   通过 {key_imp}")
            else:
                print(f"   失败 {key_imp}")
                missing.append(key_imp)
        
        return len(missing) == 0
        
    except Exception as e:
        print(f"   解析错误: {e}")
        return False

def check_functions(file_path):
    """检查函数定义"""
    print(f"\n检查 {file_path} 的函数...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        
        print(f"   找到 {len(functions)} 个函数")
        
        # 检查多模态相关函数
        multimodal_funcs = [
            'process_image_base64',
            'extract_text_from_image',
            'analyze_image_with_question',
            'multimodal_qa',
            'upload_image'
        ]
        
        print("\n检查多模态函数:")
        missing = []
        for func in multimodal_funcs:
            if func in functions:
                print(f"   通过 {func}")
            else:
                print(f"   失败 {func}")
                missing.append(func)
        
        return len(missing) == 0
        
    except Exception as e:
        print(f"   解析错误: {e}")
        return False

def check_routes(file_path):
    """检查API路由"""
    print(f"\n检查 {file_path} 的API路由...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    routes = []
    for i, line in enumerate(lines):
        if '@app.route' in line:
            # 获取路由定义
            route_line = line.strip()
            # 查找下一行的函数定义
            for j in range(i+1, min(i+5, len(lines))):
                if 'def ' in lines[j]:
                    func_name = lines[j].split('def ')[1].split('(')[0]
                    routes.append((route_line, func_name))
                    break
    
    print(f"   找到 {len(routes)} 个路由:")
    
    multimodal_routes = [
        ('/api/multimodal/qa', 'multimodal_qa'),
        ('/api/upload/image', 'upload_image')
    ]
    
    print("\n检查多模态路由:")
    missing = []
    for route_pattern, func_name in multimodal_routes:
        found = False
        for route_line, route_func in routes:
            if route_pattern in route_line and func_name == route_func:
                print(f"   通过 {route_pattern} -> {func_name}")
                found = True
                break
        
        if not found:
            print(f"   失败 {route_pattern} -> {func_name}")
            missing.append(route_pattern)
    
    return len(missing) == 0

def check_frontend(file_path):
    """检查前端代码"""
    print(f"\n检查前端文件 {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"   ❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键功能
    checks = [
        ("图像上传组件", "a-upload" in content and "handleImageUpload" in content),
        ("图片预览", "image-preview" in content and "uploadedImage" in content),
        ("多模态API调用", "/api/multimodal/qa" in content),
        ("仅分析图片功能", "analyzeImageOnly" in content),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"   通过 {check_name}")
        else:
            print(f"   失败 {check_name}")
            all_passed = False
    
    return all_passed

def main():
    """主测试函数"""
    print("=" * 60)
    print("多模态功能代码结构测试")
    print("=" * 60)
    
    backend_file = "backend/main.py"
    frontend_file = "frontend/src/views/StudentView.vue"
    
    results = []
    
    # 检查后端
    if os.path.exists(backend_file):
        results.append(("后端导入检查", check_imports(backend_file)))
        results.append(("后端函数检查", check_functions(backend_file)))
        results.append(("后端路由检查", check_routes(backend_file)))
    else:
        print(f"失败 后端文件不存在: {backend_file}")
        results.append(("后端文件", False))
    
    # 检查前端
    results.append(("前端代码检查", check_frontend(frontend_file)))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        if result:
            print(f"通过 {test_name}: 通过")
            passed += 1
        else:
            print(f"失败 {test_name}: 失败")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n所有代码结构检查通过！")
        print("   多模态功能已成功集成到项目中。")
        print("\n下一步:")
        print("   1. 安装依赖: pip install -r requirements.txt")
        print("   2. 启动后端服务进行实际测试")
        print("   3. 启动前端界面体验多模态功能")
    else:
        print("\n部分检查未通过，请查看上面的详细报告。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)