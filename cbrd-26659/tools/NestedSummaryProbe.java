import com.navercorp.cubridqa.cqt.console.bean.CaseResult;
import com.navercorp.cubridqa.cqt.console.bean.Summary;
import com.navercorp.cubridqa.cqt.console.bean.Test;
import com.navercorp.cubridqa.cqt.console.util.JunitXmlWriter;
import com.navercorp.cubridqa.cqt.console.util.TestUtil;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class NestedSummaryProbe {
    public static void main(String[] args) throws Exception {
        boolean separate = args[0].equals("separate");
        boolean nestedFailure = args.length > 1 && args[1].equals("fail");
        Test test = new Test("fixture");
        test.setTestType("sql");
        test.setScenarioRootPath("/repo/sql/");
        test.setResult_dir("/result/fixture");
        test.setRunMode(Test.MODE_RESULT);
        String parent = "/repo/sql/bugfix/";
        String[] files = {
            parent + (separate ? "direct/" : "") + "cases/direct.sql",
            parent + "nested/cases/one.sql",
            parent + "nested/cases/two.sql"
        };
        Summary nested = null;
        for (int i = 0; i < files.length; i++) {
            Map category = TestUtil.getCatMap(test, files[i]);
            Summary summary = (Summary) category.get(TestUtil.SUMMARY_KEY);
            if (summary == null) {
                summary = new Summary();
                summary.setType(Summary.TYPE_BOTTOM);
                summary.setCatPath(TestUtil.getTestCatPath(files[i], test));
                summary.setResultDir(TestUtil.getResultDir(test, files[i]));
                category.put(TestUtil.SUMMARY_KEY, summary);
            }
            CaseResult result = new CaseResult();
            result.setCaseFile(files[i]);
            result.setType(CaseResult.TYPE_SQL);
            result.setShouldRun(true);
            result.setSuccessFul(!(nestedFailure && i > 0));
            result.setTotalTime(i + 1);
            summary.getCaseList().add(result);
            if (i > 0) {
                nested = summary;
            }
        }
        TestUtil.makeSummary(test, test.getCatMap());
        List<CaseResult> emitted = new ArrayList<CaseResult>();
        Method walk = JunitXmlWriter.class.getDeclaredMethod("walk", Summary.class, List.class);
        walk.setAccessible(true);
        walk.invoke(null, test.getSummary(), emitted);
        int xmlFailures = 0;
        for (CaseResult result : emitted) {
            if (!result.isSuccessFul()) {
                xmlFailures++;
            }
        }
        System.out.printf(
            "{\"layout\":\"%s\",\"seeded_cases\":3,\"seeded_failures\":%d,"
                + "\"aggregate\":%d,\"aggregate_failures\":%d,\"junit_cases\":%d,"
                + "\"junit_failures\":%d,\"nested_total\":%d,\"nested_rows\":%d}%n",
            args[0], nestedFailure ? 2 : 0, test.getSummary().getTotalCount(),
            test.getSummary().getFailCount(), emitted.size(), xmlFailures,
            nested.getTotalCount(), nested.getCaseList().size());
        System.out.print(nested.toString());
        if (test.getSummary().getTotalCount() != 3 || emitted.size() != 3) {
            System.exit(1);
        }
    }
}
