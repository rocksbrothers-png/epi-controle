import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
const root='/workspace/i18n-full-v1/corporate/';
const output='/workspace/i18n-full-v1/audit/';
final fileMetadata=<Map<String,dynamic>>[];
final literals=<Map<String,dynamic>>[],dynamicSinks=<Map<String,dynamic>>[],producers=<Map<String,dynamic>>[],failures=<Map<String,dynamic>>[];
const uiNames={'Text','SelectableText','TextSpan','InputDecoration','Tooltip','AlertDialog','SnackBar','EpiButton','EpiChip','EpiEmptyState','EpiDialog','EpiBadge','EpiStockBadge','DropdownMenuItem','RadioListTile','CheckboxListTile','SwitchListTile','ListTile','Tab','BottomNavigationBarItem','NavigationDestination','NavigationRailDestination','AppBar'};
const labels={'label','labelText','hintText','helperText','errorText','tooltip','semanticsLabel','message','title','subtitle','emptyMessage','placeholder','confirmLabel','cancelLabel','buttonLabel'};
String short(String s,[int n=400])=>s.length>n?s.substring(0,n)+'…':s;
List<AstNode> ancestors(AstNode n){final out=<AstNode>[];for(AstNode? p=n.parent;p!=null;p=p.parent)out.add(p);return out;}
String argumentName(NamedExpression n)=>n.name.label.name;
String callName(AstNode? n){if(n is InstanceCreationExpression)return n.constructorName.toSource();if(n is MethodInvocation)return n.methodName.name;if(n is FunctionExpressionInvocation)return n.function.toSource();return '';}
String template(StringLiteral n){if(n is SimpleStringLiteral)return n.value;if(n is AdjacentStrings)return n.strings.map(template).join();if(n is StringInterpolation)return n.elements.map((e)=>e is InterpolationString?e.value:'{${(e as InterpolationExpression).expression.toSource()}}').join();return n.toSource();}
String segments(StringLiteral n){if(n is SimpleStringLiteral)return n.value;if(n is AdjacentStrings)return n.strings.map(segments).join();if(n is StringInterpolation)return n.elements.whereType<InterpolationString>().map((x)=>x.value).join();return '';}
String function(AstNode n){for(final a in [n,...ancestors(n)]){if(a is MethodDeclaration)return a.name.lexeme;if(a is FunctionDeclaration)return a.name.lexeme;if(a is ConstructorDeclaration)return short(a.toSource().split('{').first,120);}return '';}
bool language(String value){final s=value.trim();return RegExp(r'[A-Za-zÀ-ÿ]{2}').hasMatch(s)&&s.length>1;}
bool canonical(String s)=>RegExp(r'^[a-z][a-z0-9_./:-]*$').hasMatch(s)&&!{'save','cancel','confirm','search','print','name','email','password','close','retry','active','inactive','pending','approved','rejected','expired','warning','critical','normal','disabled','open','closed','resolved','sent','draft','failed','paid','refunded'}.contains(s);
class Scan extends RecursiveAstVisitor<void>{
 Scan(this.path,this.source,this.unit);final String path,source;final dynamic unit;
 int line(AstNode n)=>unit.lineInfo.getLocation(n.offset).lineNumber;
 Map<String,dynamic> base(AstNode n)=>{'path':path,'line':line(n),'offset':n.offset,'end':n.end,'function':function(n),'expression':short(n.toSource(),650)};
 @override void visitSimpleStringLiteral(SimpleStringLiteral n){record(n);super.visitSimpleStringLiteral(n);}
 @override void visitStringInterpolation(StringInterpolation n){record(n);super.visitStringInterpolation(n);}
 @override void visitAdjacentStrings(AdjacentStrings n){record(n);super.visitAdjacentStrings(n);}
 void record(StringLiteral n){
  if(n.parent is StringLiteral)return;final chain=ancestors(n);final value=template(n),literal=segments(n);var kind='unresolved_literal',confidence='candidate';String evidence='';
  final named=chain.whereType<NamedExpression>().firstOrNull;final call=chain.firstWhere((x)=>x is InstanceCreationExpression||x is MethodInvocation||x is FunctionExpressionInvocation,orElse:()=>unit.unit);final method=function(n);
  if(chain.any((x)=>x is UriBasedDirective)){kind='import_export_part';confidence='excluded';}
  else if(chain.any((x)=>x is IndexExpression&&x.index.offset<=n.offset&&n.end<=x.index.end)){kind='data_map_key';confidence='excluded';}
  else if(chain.any((x)=>x is MapLiteralEntry&&identical(x.key,n))){kind='data_map_key';confidence='excluded';}
  else if(chain.any((x)=>x.runtimeType.toString().contains('ConstantPattern'))||chain.any((x)=>x is SwitchCase&&identical(x.expression,n))){kind='canonical_case_code';confidence='excluded';}
  else if(chain.any((x)=>x is BinaryExpression&&['==','!='].contains(x.operator.lexeme)&&[x.leftOperand,x.rightOperand].contains(n))){kind='canonical_comparison';confidence='excluded';}
  else if(['print','debugPrint','debugPrintStack'].contains(callName(call))){kind='developer_log';confidence='excluded';}
  else if(['Locale'].contains(callName(call))){kind='locale_identifier';confidence='excluded';}
  else if(callName(call).startsWith('DateFormat')||callName(call).startsWith('NumberFormat')){kind='Intl_format_pattern';confidence='excluded';}
  else if(callName(call).startsWith('RegExp')){kind='regex_pattern';confidence='excluded';}
  else if(RegExp(r'^(https?://|/api/|assets/|package:|dart:|[A-Za-z0-9_./-]+\.(png|jpg|pdf|svg|ttf|dart)$)').hasMatch(value)){kind='route_url_asset';confidence='excluded';}
  else if(RegExp(r'^(pt[-_]BR|en[-_](US|GB)|es[-_]ES|fr[-_]FR|no[-_]NO|nb[-_]NO|[A-Z_]{3,})$').hasMatch(value)||['PIX','Boleto','BRL','R\$','CA','CPF','CNPJ','EPI','PPE','NR-6','N/A','START','BUSINESS','CORPORATE','ENTERPRISE'].contains(value)){kind='identifier_brand_regulatory_currency';confidence='excluded';}
  else if(value.isEmpty||!language(literal)){kind='empty_punctuation_or_interpolation_only';confidence='excluded_or_dynamic';}
  else if(chain.any((x)=>x is NamedExpression&&argumentName(x)=='validator')){kind='validator_message';confidence='verified_ui_sink';evidence='validator callback';}
  else if(callName(call).contains('Exception')||callName(call).endsWith('Error')){kind='exception_message_producer';confidence='producer_exposure_needs_trace';evidence=callName(call);}
  else if(named!=null&&labels.contains(argumentName(named))){
   final owner=named.parent?.parent;kind='named_ui_label';confidence=uiNames.contains(callName(owner).split('.').first)||callName(owner).startsWith('Epi')?'verified_ui_sink':'candidate_named_label';evidence='${callName(owner)}.${argumentName(named)}';
  }
  else if(['Text','SelectableText','TextSpan','Tooltip'].contains(callName(call).split('.').first)){kind='text_widget';confidence='verified_ui_sink';evidence=callName(call);}
  else if(chain.any((x)=>x is RecordLiteral)){
   final record=chain.whereType<RecordLiteral>().first;final field=record.fields.indexWhere((x)=>x.offset<=n.offset&&x.end>=n.end);kind='record_label_or_code';confidence=field>0?'candidate_record_display_label':'candidate_record_code_or_label';evidence='record field $field';
  }
  else if(RegExp(r'label|message|validat|error|default|title|_status|_method|_cycle',caseSensitive:false).hasMatch(method)){kind='label_or_message_formatter';confidence='producer_exposure_needs_trace';evidence=method;}
  else if(chain.any((x)=>x.runtimeType.toString().contains('DefaultFormalParameter'))){kind='default_parameter';confidence=path.contains('epi_design')?'candidate_design_default':'candidate_default';}
  else if(path.contains('/core/bloc/')){kind='cubit_literal';confidence='producer_exposure_needs_trace';}
  else if(canonical(value)){kind='canonical_token_candidate';confidence='excluded_candidate_not_proven';}
  final ctx=chain.take(7).map((x)=>x.runtimeType.toString().replaceAll('Impl','')).toList();
  literals.add({...base(n),'expression_kind':n is AdjacentStrings?'adjacent':n is StringInterpolation?'interpolation':'simple','text_template':value,'literal_segments':literal,'usage_kind':kind,'confidence':confidence,'sink_evidence':evidence,'named_argument':named==null?null:argumentName(named),'ancestor_types':ctx});
 }
 @override void visitInstanceCreationExpression(InstanceCreationExpression n){
  final name=n.constructorName.type.toSource();
  if(['Text','SelectableText','TextSpan'].contains(name)){
   for(final arg in n.argumentList.arguments){final expression=arg is NamedExpression?arg.expression:arg;if(arg is NamedExpression&&argumentName(arg)!='text')continue;if(expression is StringLiteral&&expression.stringValue!=null)continue;final txt=expression.toSource();if(RegExp(r'error|message|success|snapshot|reason|failure',caseSensitive:false).hasMatch(txt))dynamicSinks.add({...base(expression),'widget':name,'usage_kind':RegExp(r'l10n|AppLocalizations|\.billing|\.feedback').hasMatch(txt)?'localized_wrapper_with_dynamic_detail':'raw_dynamic_message_sink','consumer_expression':txt});}
  }
  super.visitInstanceCreationExpression(n);
 }
 @override void visitMethodInvocation(MethodInvocation n){
  if(['Text','SelectableText','TextSpan'].contains(n.methodName.name)){
   for(final arg in n.argumentList.arguments){final expression=arg is NamedExpression?arg.expression:arg;if(arg is NamedExpression&&argumentName(arg)!='text')continue;if(expression is StringLiteral&&expression.stringValue!=null)continue;final txt=expression.toSource();if(RegExp(r'error|message|success|snapshot|reason|failure',caseSensitive:false).hasMatch(txt))dynamicSinks.add({...base(expression),'widget':n.methodName.name,'usage_kind':RegExp(r'l10n|AppLocalizations|\.billing|\.feedback').hasMatch(txt)?'localized_wrapper_with_dynamic_detail':'raw_dynamic_message_sink','consumer_expression':txt});}
  }
  super.visitMethodInvocation(n);
 }
 @override void visitNamedExpression(NamedExpression n){
  final name=argumentName(n),text=n.expression.toSource();
  if(path.contains('/core/bloc/')&&RegExp(r'error|success|message|failure',caseSensitive:false).hasMatch(name)&&text!='null')producers.add({...base(n),'field':name,'producer_expression':text,'usage_kind':n.expression is StringLiteral?'literal_state_message':'dynamic_state_message'});
  super.visitNamedExpression(n);
 }
 @override void visitReturnStatement(ReturnStatement n){
  if(path.contains('/core/bloc/')&&RegExp(r'error|message',caseSensitive:false).hasMatch(function(n)))producers.add({...base(n),'field':'return','producer_expression':n.expression?.toSource(),'usage_kind':'error_message_return'});
  super.visitReturnStatement(n);
 }
}
void main(){final files=<File>[];for(final rel in ['flutter/packages/epi_api/lib']){for(final e in Directory(root+rel).listSync(recursive:true,followLinks:false)){if(e is File&&e.path.endsWith('.dart')&&!e.path.contains('/generated/'))files.add(e);}}files.sort((a,b)=>a.path.compareTo(b.path));
for(final f in files){final path=f.path.substring(root.length);try{final source=f.readAsStringSync();fileMetadata.add({'path':path,'sha256_of_parsed_source':sha256.convert(utf8.encode(source)).toString(),'lines':source.split('\n').length});final result=parseString(content:source,throwIfDiagnostics:false);if(result.errors.any((e)=>e.errorCode.type.name=='SYNTACTIC_ERROR'))failures.add({'path':path,'errors':result.errors.map((e)=>e.toString()).toList()});result.unit.accept(Scan(path,source,result));}catch(e){failures.add({'path':path,'error':e.toString()});}}
final data={'files_parsed':files.length,'file_metadata':fileMetadata,'timestamp_utc':DateTime.now().toUtc().toIso8601String(),'scope':['epi_api lib adjacent transport/error/model producers'],'literals':literals,'dynamic_ui_sinks':dynamicSinks,'cubit_message_producers':producers,'parse_failures':failures,'limits':['Syntactic AST only, no type-resolution or execution.','Classifications are triage; excluded_candidate values are not proven exempt.','Adjacent/interpolated strings counted as outer expressions; inner expression literals can have separate semantic occurrences.','Generated localizations excluded intentionally; catalogs/localization quality require separate review.']};File(output+'flutter-api-ast-inventory.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert(data));print(jsonEncode({'files':files.length,'literal_expressions':literals.length,'dynamic_ui_sinks':dynamicSinks.length,'message_producers':producers.length,'parse_failures':failures.length}));}
