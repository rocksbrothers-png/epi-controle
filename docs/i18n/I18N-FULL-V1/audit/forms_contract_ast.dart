import 'dart:io';
import 'dart:convert';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
const root='/workspace/i18n-full-v1/corporate';
class V extends RecursiveAstVisitor<void>{
 final calls=<String>[], rules=<String>[];
 @override void visitMethodInvocation(MethodInvocation n){if(n.target?.toSource().startsWith('ApiClient.')==true)calls.add(n.toSource());super.visitMethodInvocation(n);}
 @override void visitVariableDeclaration(VariableDeclaration n){if(['_roles','_unitTypes','body','canEdit'].contains(n.name.lexeme))rules.add(n.toSource());super.visitVariableDeclaration(n);}
 @override void visitMethodDeclaration(MethodDeclaration n){if(['_needsEmployee','_parseYears','_onDetect','_showResult','_generatePassword','_copyPassword'].contains(n.name.lexeme)&&n.name.lexeme!='_copyPassword')rules.add(n.toSource());super.visitMethodDeclaration(n);}
}
void main(){final out=<Map<String,dynamic>>[];for(final feature in ['users/users_screen','units/units_screen','settings/archival_policy_screen','qr/qr_scanner_screen']){final path='flutter/apps/epi_admin/lib/features/$feature.dart';final old=Process.runSync('git',['show','HEAD:$path'],workingDirectory:root).stdout as String;final current=File('$root/$path').readAsStringSync();final a=V(),b=V();parseString(content:old).unit.accept(a);parseString(content:current).unit.accept(b);out.add({'path':path,'api_calls_equal':jsonEncode(a.calls)==jsonEncode(b.calls),'api_calls':b.calls,'rules_equal':jsonEncode(a.rules)==jsonEncode(b.rules),'rules':b.rules});}File('/workspace/i18n-full-v1/audit/flutter-forms-contracts.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert(out));for(final x in out)print('${x['path']}: API equal=${x['api_calls_equal']}; rules equal=${x['rules_equal']}');}
